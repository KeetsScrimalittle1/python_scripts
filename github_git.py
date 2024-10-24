import os
from shutil import rmtree
import re
import git
from datetime import datetime
from uuid import uuid4
import requests
import json

class Github_Git:
    """Use to execute git commands and work with a github repository"""
    def __init__(self, project:str, username:str, password:str):
        """Initialize enterprise, project, repo_name, repo_id, username, password. Username needs to be the github formatted username.
        Password will be a token, authenticating with user passwords is deprecated."""
        self.project = project
        self.username = username
        self.password = password
    def validate_path(self, path_string):
        """Use to validate a given path string"""
        uniregx = r'^(\/?[a-zA-Z0-9_\-@.]+)+$'
        winregx = r'(?:\\\\[^\\]+|[a-zA-Z]:)((?:\\[^\\]+)+\\)?([^<>:]*)'
        try:
            if os.name == 'nt':
                return re.match(winregx, path_string)
            elif os.name == 'posix':
                return re.match(uniregx, path_string)
            else:
                ex_msg = f"'{path_string}' is not a valid posixpath or ntpath format.\n\n{e}"
                print(ex_msg)
                raise Exception(ex_msg)
        except Exception as e:
            ex_msg = f"[-] Failed to validate path string of '{path_string}'\n\n{e}"
            print(ex_msg)
            raise Exception(ex_msg)
    def github_clone(self, repo_name:str, repo_dir:str, force:bool=False):
        """Use to clone a github enterprise repository. Specify a full path for the ouput directory"""
        self.repo_name = repo_name
        self.repo_dir = repo_dir
        try:
            if not self.username or not self.password:
                ex_msg = f"[-] Failed clone {self.repo_name} into directory {self.repo_dir}: 'No username or token password specified'\n\n{e}"
                print(ex_msg)
                raise Exception(ex_msg)
        except:
            ex_msg = f"[-] Failed clone {self.repo_name} into directory {self.repo_dir}: 'No username or token password specified'\n\n{e}"
            print(ex_msg)
            raise Exception(ex_msg)
 
        if self.validate_path(repo_dir):
            if os.path.exists(self.repo_dir):
                if os.listdir(self.repo_dir):
                    try:
                        rmtree(self.repo_dir)
                        os.mkdir(self.repo_dir)
                    except Exception as e:
                        if force:
                            try:
                                self.repo_dir = os.path.join(self.repo_dir, f"clone_{datetime.today().strftime('%Y%m%d_%H%M')}")
                                os.mkdir(self.repo_dir)
                            except Exception as e:
                                try:
                                    self.repo_dir = os.path.join(self.repo_dir, f"clone_{str(uuid4())}")
                                    os.mkdir(self.repo_dir)
                                except Exception as e:
                                    ex_msg = f"[-] Provided directory is not empty and creation of a sub directory failed.\
                                        Ensure directory is empty prior to cloning into it. {self.repo_dir}\n\n{e}"
                                    print(ex_msg)
                                    raise Exception(ex_msg)
                        else:
                            ex_msg = f"[-] Provided directory is not empty and deletion of directory failed.  Ensure directory is empty prior to "\
                                f"cloning into it, or use the force paramater to create a unique sub directory at {self.repo_dir}"
                            print(ex_msg)
                            raise Exception(ex_msg)
                else:
                    pass
            else:
                try:
                    os.mkdir(self.repo_dir)
                except:
                    ex_msg = f"Failed to create directory '{self.repo_dir}'. Manually create this directory and try again."
                    print(ex_msg)
                    raise Exception(ex_msg)
            self.repo_url = fhttps://{self.username}:{self.password}@github.com/{self.project}/{repo_name}
            try:
                repo = git.Repo.clone_from(url=self.repo_url, to_path=os.path.join(f"{self.repo_dir}",f"{self.repo_name}"))
                self.repo = repo
                self.remote_ref = self.repo.head.reference.name
                return self.repo
            except Exception as e:
                ex_msg = f"[-] Failed to clone {self.repo_name} into directory {self.repo_dir} using url "\
                    f"{self.repo_url.replace(self.password, '<password>')}\n\n{str(e).replace(self.password, '<password>')}"
                print(ex_msg)
                raise Exception(ex_msg)
        else:
            print(f"[-] Unable to determine if {self.repo_dir} is a valid directory for use.")
            return self.return_code(1)
    def github_create_branch(self, branch_name:str):
        """Use to create and checkout out a new branch, based off the main branch, and push it to the remote repository."""
        self.branch_name = branch_name
        try:
            new_branch = self.repo.create_head(branch_name)
            self.new_branch = new_branch
            self.repo.head.reference = new_branch
            self.repo.git.add(self.repo.working_dir)
            return self.new_branch
        except Exception as e:
            ex_msg = f"[-] Failed create new branch {self.branch_name} from main and push to remote.\n\n{e}"
            print(ex_msg)
            raise Exception(ex_msg)
    def commit_changes(self, message:str=None):
        """Use to commit all staged changes"""
        if message:
            pass
        else:
            message = f"Pushing new changes to {self.new_branch}."
        try:
            stage = self.repo.git.add(self.repo.working_dir)
            commit_output = self.repo.git.commit(m=f"{message}")
            return commit_output
        except Exception as e:
            ex_msg = f"[-] Failed to commit changes to {self.branch_name} and push to remote.\n\n{e}"
            print(ex_msg)
            raise Exception(ex_msg)
    def push_changes(self):
        """Use to push all committed changes and push to remote"""
        try:
            push_output =self.repo.git.push('--set-upstream', self.repo.remote().name, self.new_branch)
            return push_output
        except Exception as e:
            ex_msg = f"[-] Failed to commit changes to {self.branch_name} and push to remote.\n\n{e}"
            print(ex_msg)
            raise Exception(ex_msg)
    def create_pr(self, pr_title:str, pr_description:str):
        """Use to create a pull request from new branch to main"""
        out_keys = ["id", "html_url", "state", "title", "body", "created_at", "commits", "additions", "deletions", "changed_files"]
        headers = {f"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.password}", "X-GitHub-Api-Version": f"2022-11-28"}
        pr_uri = fhttps://api.github.com/repos/{self.project}/{self.repo_name}/pulls
        payload = {"title":pr_title, "body":pr_description, "head": self.new_branch.name, "base": self.remote_ref}
        try:
            pr_res = requests.post(pr_uri, data=json.dumps(payload), headers=headers)
            if pr_res.status_code != 201:
                ex_msg = f"Failed to generate pull request for branch {self.new_branch.name}.\n\n'Status:', {pr_res.status_code}, "\
                    f"'Headers:', {pr_res.headers}, 'Error Response:',{pr_res.text}"
                print(ex_msg)
                raise Exception(ex_msg)
            else:
                pr_out={}
                for outk in out_keys:
                    pr_out.update({f"{outk}":pr_res.json()[outk]})
                pr_out.update({'comments_url': pr_res.json()['_links']['comments']['href']})
                self.pr_info = pr_out
                return self.pr_info
        except Exception as e:
            ex_msg = f"[-] Failed to create a pull request under {self.project}/{self.repo_name} for changes.\n\n{e}"
            print(ex_msg)
            raise Exception(ex_msg)
    def add_pr_message(self, message:str, comments_url:str=None):
        """Use to add comments to an existing pr"""
        if comments_url:
            comments_uri = comments_url
        else:
            try:
                comments_uri = self.pr_info['comments_url']
            except Exception as e:
                ex_msg = f"Failed to add comments to pull request.  Either specify an existing pull request comments url or create a new pull request using create_pr.\n\n{e}"
                print(ex_msg)
                raise Exception(ex_msg)
            payload = {"body":message}
            headers = {f"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.password}", "X-GitHub-Api-Version": f"2022-11-28"}
            message_res = requests.post(comments_uri, data=json.dumps(payload), headers=headers)
            if message_res.status_code != 201:
                ex_msg = f"Failed to add comments to existing pull request.\n\nstatus:{message_res.status_code} message:{message_res.json()['message']}"
                print(ex_msg)
                raise Exception(ex_msg)
            else:
                return f"Successfully added message to {comments_uri}."

