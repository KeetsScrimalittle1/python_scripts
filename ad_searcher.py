## -- todo -- add exclude empty ous or remove the empty dictionary from the resulting yaml to decrease inventory size
## -- todo -- add better error output instead of one large try except
## -- todo -- add the ability to create yaml or ini inventory
from ldap3 import Server, Connection
from copy import deepcopy
import re
           
class AD_DN_Searcher:
    """
    Use to search an ad ou structure from a starting dn path
    """
    def __init__(self):
        """Initialize the domain controller to connect to."""
    def dc_connect(self, domain_controller:str, user_name:str=None, password:str=None):
        """Use to create initial connection to a domain controller"""
        self.domain_controller = domain_controller
        try:
            dc = Server(self.domain_controller)
        except Exception as e:
            print(f"[-] Failed to connect to DC {self.domain_controller}\n\n\n{e} using account: {user_name}")
            raise Exception(f"Failed to connect to DC {self.domain_controller}\n\n\n{e} using account: {user_name}")
        #create ldap connection
        try:
            if not (user_name or password):
                connection = Connection(server=dc, fast_decoder=True, read_only=True, 
                                        client_strategy='SAFE_RESTARTABLE', auto_bind=True)
                print(f"[-] Not specifying a username and password to create the connection with will usually generate empty results. {self.domain_controller}\n\n\n{e}")
            else:
                connection = Connection(server=dc, user=user_name, password=password,
                                            fast_decoder=True, read_only=True,
                                            client_strategy='SAFE_RESTARTABLE', auto_bind=True)
            self.connection = connection
        except Exception as e:
            print(f"[-] Failed to connect to DC {self.domain_controller}\n\n\n{e}")
            raise Exception(f"Failed to connect to DC {self.domain_controller}\n\n\n{e}")
    def dc_disconnect(self, connection:Connection=None):
        """Use to close connection to a domain controller"""
        try:
            if connection:
                discc = connection.unbind()
            else:
                discc = self.connection.unbind()
            return discc
        except Exception as e:
            print(f"[-] Failed to unbind DC. A connection object was not supllied. Either create the object with the dc_connect method or supply a connection object using the connection paramter. \n\n\n{e}")
            raise Exception(f"Failed to unbind DC. A connection object was not supllied. Either create the object with the dc_connect method or supply a connection object using the connection paramter. \n\n\n{e}")
    def create_dn_dict(self, base_dn:str, include_children_key:bool=True, all_replace_name:str='all_servers'):
        """Use to build initial dictionary for dn sub ou search"""
        self.base_dn = base_dn.lower()
        try:
            self.domain = re.findall(r'(?<=dc=)(.*)',self.base_dn)[0]
            self.base_dn_array = [x.lower().replace('ou=','').replace('dc=','').lower() for x in self.base_dn.split(',') if x != self.domain.split(',')[-1]]
            #replace special characters with underscores and remove any all keys
            dict_array_formatted = [re.sub(r'[-\/\\]', '_', x).replace(' ','') for x in self.base_dn_array]
            [x.replace('all', all_replace_name) for x in dict_array_formatted if x == 'all']
            if include_children_key:
                [dict_array_formatted.insert(x,'children') for x in range(len(self.base_dn_array)*2)[::2]]
                dict_array_formatted.pop(0)
            base_dn_tree = {}
            for key in dict_array_formatted:
                base_dn_tree = {key: base_dn_tree}
            self.base_dn_tree = base_dn_tree
            return {'keys': dict_array_formatted,'dictionary':self.base_dn_tree}
        except Exception as e:
            print(f"[-]Function create_dn_dict(), Failed to create base dn dictionary object.\n\n\n{e}")
            raise Exception(f"Function create_dn_dict(), Failed to create base dn dictionary object.\n\n\n{e}")
    def get_child_ou_dns(self, distinguished_name, filter:str=None):
        """Search sub OUs in a given ou add to a list and output"""
        try:
            if not self.connection:
                print(f"[-] Need to create a connection object prior to running")
        except:
            print(f"[-] Need to create a connection object prior to running\n\n Use dc_connect method")
        results = []
        if filter:
            search_filter = filter
        else:
            search_filter = '(objectCategory=organizationalUnit)'
            elements = self.connection.extend.standard.paged_search(
            search_base=distinguished_name,
            search_filter=search_filter,
            search_scope='LEVEL',
            paged_size=100)
        try:
            for element in elements:
                if 'dn' in element:
                    if element['dn'] != distinguished_name:
                        if 'dn' in element:
                            results.append(element['dn'].lower())
        except:
            pass
        return(results)
    def get_ad_hosts(self, distinguished_name, attributes:list=None, name_only=False, osfilter:str=None):
        try:
            if not self.connection:
                print(f"[-] Need to create a connection object prior to running")
        except:
            print(f"[-] Need to create a connection object prior to running\n\n Use dc_connect method")
        results = {}
        hosts_list = []
        if osfilter:
            if osfilter.lower() == 'linux':
                search_filter = '(&(objectCategory=computer)(operatingSystem=*linux*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))' #exclude disabled computer accounts
            elif osfilter.lower() == 'windows':
                search_filter = '(&(objectCategory=computer)(operatingSystem=windows*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))' #exclude disabled computer accounts
            else:
                return(Exception('osfilter must be either "linux" or "windows" default is no os filter applied')) #naughty naughty
        else:
            search_filter = '(&(objectCategory=computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))' #exclude disabled computer accounts
        if attributes:
            attributes = attributes
        else:
            attributes = ['dNSHostName']
        elements = self.connection.extend.standard.paged_search(
            search_base=distinguished_name,
            search_filter=search_filter,
            search_scope='LEVEL',
            attributes=attributes,
            paged_size=100)
        if name_only:
            for element in elements:
                if 'dn' in element:
                    if element['attributes']['dNSHostName']:
                        hosts_list.append(element['attributes']['dNSHostName'].lower())
            for hl in reversed(hosts_list):
                results[hl] = None
        else:
            for element in elements:
                host = {}
                [host.update({k:v}) for k,v in element['attributes'].items()]
                results[element['attributes']['name'].lower()] = host
        return(results)
    def search_dn_recursive(self, include_base_ou:bool, base_dn:str='', include_children_key:bool=True, append_ou_names:bool=True,
                            exclude_top_ou:bool=False, base_dn_dict:dict=None):
        """Use to recursively search a dn for child ous and systems. Requires full dn path."""
        try:
            if not self.connection:
                print(f"[-] AD connection object was not defined. Need to create a connection object prior to running")
                raise Exception(f"AD connection object was not defined. Need to create a connection object prior to running")
        except Exception as e:
            print(f"[-] Need to create a connection object prior to running.\nUse dc_connect method\n\n{e}")
            raise Exception(f"AD connection object was not defined. Need to create a connection object prior to running.\nUse dc_connect method\n\n{e}")
        if base_dn_dict:
            ou_tree = deepcopy(base_dn_dict)
        else:
            try:
                if self.base_dn_array:
                    #already set through the create_dn_dict function
                    #needs more testing
                    pass
            except Exception as e:
                try:
                    if base_dn != '':
                        self.base_dn = base_dn.lower()              
                        self.domain = re.findall(r'(?<=dc=)(.*)',self.base_dn)[0]
                        self.base_dn_array = [x.lower().replace('ou=','').replace('dc=','').lower() for x in self.base_dn.split(',') if x != self.domain.split(',')[-1]]
                    else:
                        print((f"[-] Failed to find a base dn dictionary object. Run create_dn_object method prior searching, "\
                                        f"or supply a dictionary object to the base_dn_dict or a dn path string to the base_dn paramater\n\n{self.base_dn}"))
                        raise Exception (f"Failed to find a base dn dictionary object. Run create_dn_object method prior searching, "\
                                        f"or supply a dictionary object to the base_dn_dict or a dn path string to the base_dn paramater\n\n{self.base_dn}")
                except Exception as e:
                    raise Exception(f"Failed to build a base dn dictionary object. validate the dn path string and try again\n{self.base_dn}\n\n{e}")
            try:
                ou_tree = {self.base_dn_array[0]:{}}
            except Exception as e:
                print(f"[-] Failed to find a base dn dictionary object. Run create_dn_object method prior searching, or supply a dictionary object to the base_dn_dict paramater\n\n\n{e}")
                raise Exception(f"Failed to find a base dn dictionary object. Run create_dn_object method prior searching, or supply a dictionary object to the base_dn_dict paramater\n\n\n{e}")
        #create process info dictionary and dictionary for output
        all_ous = {}
        ou_dn_process_status = {}
        ou_dn_process_status[self.base_dn] = {'need_to_process':True}
        has_searches_to_process = True
        try:
            #loop through all ous level by level and build the dictionary for yaml
            while has_searches_to_process:
                #get the dn of the ous to process
                ou_dn_process_status_keys = list(ou_dn_process_status.keys())
                #check list of ous to process
                for dn in ou_dn_process_status_keys:
                    #search for child ous
                    if ou_dn_process_status[dn]['need_to_process']:
                        #get any child ous
                        child_ous = self.get_child_ou_dns(distinguished_name=dn)
                        child_ou_dict = {}
                        all_ous[dn] = {}
                        #update dictionary with full distinguished name for searching
                        [all_ous[dn].update({x.lower():{}}) for x in child_ous]
                        #create a list of the dn path leaving out the top level path
                        dn_array = [x.lower().replace('ou=','').replace('dc=','') for x in dn.split(',') if x != self.domain.lower().split(',')[-1]]
                        dn_array = [x for x in dn_array if x not in self.base_dn_array[1:]]
                        #deep copy the dn list and create a new list to update with children
                        dict_array = deepcopy(dn_array)
                        #replace special characters with underscore, get rid of 'all' ou in dn array
                        dict_array_form = [re.sub(r'\ball\b','all_servers',re.sub(r'[-\/\\]', '_', x).replace(' ',''))for x in dict_array]
                        #create a list with just the ou name, replace all, and if child ous add them as a child dictionary, after formatting
                        child_ous_form = [re.sub(r'\ball\b','all_servers',re.sub(r'[-\/\\]', '_', c.lower().split(',')[0].replace('ou=','')).replace(' ','')) for c in child_ous]
                        #new list for formatted key names to prevent duplicate inventory group names
                        dict_array_ansible = []
                        dict_array_ansible = []
                        for i,v in enumerate(dict_array_form):
                            if append_ou_names:
                                if len(dict_array_form) > 1:
                                    if i == (len(dict_array_form)-1):
                                        dict_array_ansible.append(v)
                                    else:
                                        if include_base_ou:
                                            #join ou names into one string
                                            k_str = '_'.join(reversed(dict_array_form[i:]))
                                            #append parent key name to sub key name
                                            dict_array_ansible.append(k_str)
                                        else:
                                            #dont modify the first sub ou names with base
                                            k_str = '_'.join(reversed(dict_array_form[i:-1]))
                                            dict_array_ansible.append(k_str)
                                else:
                                    #dont modify the base ou names
                                    dict_array_ansible.append(v)
                            else:
                                dict_array_ansible.append(v)
                        if append_ou_names:
                            #modify the child ou names
                            if not include_base_ou:
                                #check if this is the base ou
                                if len(dict_array_ansible) > 1:
                                    child_ous_form = [f"{dict_array_ansible[0]}_{x}" for x in child_ous_form]
                            else:
                                child_ous_form = [f"{dict_array_ansible[0]}_{x}" for x in child_ous_form]
                        #update the empty child ou dictionary with the children ous after formatted
                        [child_ou_dict.update({c:{}}) for c in child_ous_form]
                        #add the children key needed for ansible sub groups
                        if include_children_key:
                            [dict_array_ansible.insert(x,'children') for x in range(len(dn_array)*2)[::2]]
                            #remove first instance of children key
                            dict_array_ansible.pop(0)
                        #build the dictionary string
                        dict_str = f"""ou_tree['{"']['".join([x for x in reversed(dict_array_ansible)])}']"""
                        #build string to create new dictionary with child ous
                        if child_ou_dict:
                            add_ou_key = f"""{dict_str} = {{}}"""
                            exec(add_ou_key)
                            if include_children_key:
                                add_new_dict = f"""{dict_str}['children'] = {child_ou_dict}"""
                            else:
                                add_new_dict = f"""{dict_str} = {child_ou_dict}"""
                        else:
                            add_new_dict = f"""{dict_str} = {child_ou_dict}"""
                        #execute the string to create the new dictionary
                        exec(add_new_dict)
                        #mark this ou as processed
                        ou_dn_process_status[dn]['need_to_process'] = False
                        #loop through child ous and add to process list
                        if all_ous[dn]:
                            for child_ou_dn in all_ous[dn]:
                                if not child_ou_dn in ou_dn_process_status:
                                    ou_dn_process_status[child_ou_dn] = {'need_to_process':True}
                        #look for any hosts in ou
                        child_hosts = {'hosts':self.get_ad_hosts(distinguished_name=dn, name_only=True)}
                        #if hosts exist in the ou, update dictionary with hosts list
                        if child_hosts['hosts']:
                            #build string to update dictionary with hosts
                            update_value = f"""{dict_str}.update({child_hosts})"""
                            exec(update_value)
                        else:
                            if not child_ous:
                                #remove the empty dictionary if no child ous or hosts
                                remove_dict = f"""{dict_str} = None"""
                                exec(remove_dict)
                                #if removing all empty will need to walk back up the tree until last populated dictionary
                #check if more ous to search
                has_searches_to_process = False
                for dn in ou_dn_process_status:
                    if ou_dn_process_status[dn]['need_to_process']:
                        has_searches_to_process = True
            return ou_tree
        except Exception as e:
            print(f"[-] Failed to recursively search base dn and create a dictionary tree. "\
                f"Arguments:\n{self.domain}\n{self.base_dn}\n{include_base_ou}\n\n{ou_dn_process_status}")
            raise Exception(f"Failed to recursively search base dn and create a dictionary tree.\n\n{e}")
 

