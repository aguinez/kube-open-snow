# kubesol/integrations/github_api.py
from github import Github, UnknownObjectException, GithubException
from github.AuthenticatedUser import AuthenticatedUser
from github.Organization import Organization
import os
import base64
from kubesol.constants import GITHUB_ORG_OR_USER, GITHUB_TOKEN_SECRET_NAME, PROJECT_ID_LABEL_KEY, PROJECT_NAME_LABEL_KEY

try:
    # CAMBIO CRUCIAL AQUÍ: Importa el módulo completo y le da un alias
    import kubesol.core.k8s_api as k8s_api # <--- CAMBIO EN ESTA LÍNEA
except ImportError as e:
    print(f"🚨 Critical ImportError: Could not load kubesol.core.k8s_api module: {e}")
    k8s_api = None

_github_client = None

def _get_github_client():
    global _github_client
    if _github_client is None:
        try:
            # Uso de k8s_api con el alias
            secret_data = k8s_api.get_secret_data(name=GITHUB_TOKEN_SECRET_NAME, namespace='default')
            if not secret_data or 'token' not in secret_data:
                raise ValueError(f"GitHub token not found in Secret '{GITHUB_TOKEN_SECRET_NAME}' in namespace 'default' or missing 'token' key.")
            
            github_token = secret_data['token']
            _github_client = Github(github_token)
            
            user = _github_client.get_user()
            print(f"✅ GitHub client initialized successfully for user: {user.login}")
            
        except UnknownObjectException:
            print(f"❌ GitHub token invalid or insufficient permissions for user or organization access.")
            _github_client = None
        except GithubException as e:
            print(f"❌ GitHub API error during client initialization: {e}")
            _github_client = None
        except ValueError as e:
            print(f"❌ Configuration error for GitHub client: {e}")
            _github_client = None
        except Exception as e:
            print(f"❌ Unexpected error during GitHub client initialization: {type(e).__name__} - {e}")
            _github_client = None
    return _github_client


def _get_target_entity(client: Github):
    if not client: return None
    
    if GITHUB_ORG_OR_USER:
        try:
            org = client.get_organization(GITHUB_ORG_OR_USER)
            return org
        except UnknownObjectException:
            authenticated_user = client.get_user()
            if authenticated_user.login == GITHUB_ORG_OR_USER:
                return authenticated_user
            else:
                print(f"❌ Configured GitHub entity '{GITHUB_ORG_OR_USER}' is not an organization, and does not match the authenticated user '{authenticated_user.login}'. Cannot operate on arbitrary users.")
                return None
        except Exception as e:
            print(f"❌ Error resolving target GitHub entity '{GITHUB_ORG_OR_USER}': {e}")
            return None
    else:
        return client.get_user()

def _get_repo_object(client: Github, repo_name: str):
    target_entity = _get_target_entity(client)
    if not target_entity: return None

    try:
        if isinstance(target_entity, Organization):
            return target_entity.get_repo(repo_name)
        elif isinstance(target_entity, AuthenticatedUser):
            return target_entity.get_repo(repo_name)
        else:
            print(f"❌ Internal Error: Unexpected target entity type: {type(target_entity)}")
            return None
    except UnknownObjectException:
        print(f"🤷 Repository '{repo_name}' not found under '{target_entity.login}'.")
        return None
    except GithubException as e:
        print(f"❌ GitHub API error getting repository '{repo_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting repository '{repo_name}': {type(e).__name__} - {e}")
        return None

def _get_organization_or_user(client):
    try:
        if GITHUB_ORG_OR_USER:
            try:
                org = client.get_organization(GITHUB_ORG_OR_USER)
                return org
            except UnknownObjectException:
                user = client.get_user(GITHUB_ORG_OR_USER)
                return user
        else:
            return client.get_user()
    except Exception as e:
        print(f"❌ Error getting GitHub organization/user '{GITHUB_ORG_OR_USER}': {e}")
        return None

def create_github_repository(repo_name: str, description: str = "") -> str | None:
    client = _get_github_client()
    if not client: return None

    target_entity = _get_target_entity(client)
    if not target_entity: return None

    try:
        print(f"ℹ️ Attempting to create GitHub repository '{repo_name}' under '{target_entity.login}'...")
        
        if isinstance(target_entity, Organization):
            repo = target_entity.create_repo(repo_name, description=description, private=False)
        elif isinstance(target_entity, AuthenticatedUser):
            repo = target_entity.create_repo(repo_name, description=description, private=False)
        else:
            print(f"❌ Internal Error: Cannot create repository on unexpected entity type: {type(target_entity)}")
            return None
            
        print(f"✅ GitHub repository '{repo.full_name}' created successfully: {repo.html_url}")
        return repo.html_url
    except GithubException as e:
        if e.status == 422 and "name already exists" in e.data.get('message', ''):
            print(f"ℹ️ GitHub repository '{repo_name}' already exists. Skipping creation.")
            repo = _get_repo_object(client, repo_name)
            if repo: return repo.html_url
            else: return None
        print(f"❌ Error creating GitHub repository '{repo_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error creating GitHub repository '{repo_name}': {type(e).__name__} - {e}")
        return None


def create_github_branch(repo_name: str, branch_name: str, base_branch: str) -> bool:
    client = _get_github_client()
    if not client: return False

    repo = _get_repo_object(client, repo_name)
    if not repo: return False

    try:
        base_branch_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_commit_sha = base_branch_ref.object.sha

        print(f"ℹ️ Attempting to create branch '{branch_name}' from '{base_branch}' (SHA: {base_commit_sha}) in repo '{repo_name}'...")
        repo.create_git_ref(f"refs/heads/{branch_name}", base_commit_sha)
        print(f"✅ GitHub branch '{branch_name}' created successfully in '{repo_name}'.")
        return True
    except UnknownObjectException:
        print(f"❌ Base branch '{base_branch}' not found in repository '{repo_name}'. Cannot create new branch '{branch_name}'.")
        return False
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in e.data.get('message', ''):
            print(f"ℹ️ GitHub branch '{branch_name}' already exists in '{repo_name}'. Skipping creation.")
            return True
        print(f"❌ Error creating GitHub branch '{branch_name}' in '{repo_name}': {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating GitHub branch '{branch_name}' in '{repo_name}': {type(e).__name__} - {e}")
        return False


def get_file_content_from_github(repo_name: str, branch_name: str, file_path: str) -> str | None:
    client = _get_github_client()
    if not client: return None

    repo = _get_repo_object(client, repo_name)
    if not repo: return None

    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        if isinstance(contents, list):
            print(f"❌ '{file_path}' is a directory, not a file, in branch '{branch_name}' of '{repo_name}'.")
            return None
        return base64.b64decode(contents.content).decode('utf-8')
    except UnknownObjectException:
        print(f"ℹ️ File '{file_path}' not found in branch '{branch_name}' of '{repo_name}'.")
        return None
    except GithubException as e:
        print(f"❌ GitHub API error getting file '{file_path}' from '{repo_name}/{branch_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting file content from GitHub: {type(e).__name__} - {e}")
        return None

def create_or_update_github_file(repo_name: str, branch_name: str, file_path: str, commit_message: str, content: str) -> bool:
    client = _get_github_client()
    if not client: return False

    repo = _get_repo_object(client, repo_name)
    if not repo: return False

    try:
        print(f"ℹ️ Attempting to create file '{file_path}' in branch '{branch_name}' of '{repo_name}'...")
        repo.create_file(file_path, commit_message, content, branch=branch_name)
        print(f"✅ File '{file_path}' created successfully in branch '{branch_name}' of '{repo_name}'.")
        return True
    except GithubException as e:
        if e.status == 422:
            print(f"ℹ️ Creation failed (status 422). Assuming file '{file_path}' already exists in branch '{branch_name}'. Attempting to update...")
            
            try:
                file_obj = repo.get_contents(file_path, ref=branch_name)
                if isinstance(file_obj, list):
                     print(f"❌ Cannot update: '{file_path}' is a directory, not a file, in branch '{branch_name}' of '{repo_name}'.")
                     return False

                existing_content = base64.b64decode(file_obj.content).decode('utf-8')
                if existing_content == content:
                    print(f"ℹ️ File '{file_path}' in branch '{branch_name}' is already identical. Skipping update.")
                    return True
                
                repo.update_file(file_path, commit_message, content, file_obj.sha, branch=branch_name)
                print(f"✅ File '{file_path}' updated successfully in branch '{branch_name}' of '{repo_name}'.")
                return True
            except UnknownObjectException:
                print(f"❌ Error: File '{file_path}' was reported as existing but could not be retrieved for update (UnknownObjectException).")
                return False
            except GithubException as update_e:
                print(f"❌ GitHub API error updating file '{file_path}' in '{repo_name}/{branch_name}': {update_e}")
                return False
        else:
            print(f"❌ GitHub API error creating/updating file '{file_path}' in '{repo_name}/{branch_name}': {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error creating/updating GitHub file: {type(e).__name__} - {e}")
        return False

def create_github_pull_request(repo_name: str, title: str, head_branch: str, base_branch: str, body: str = "") -> str | None:
    client = _get_github_client()
    if not client: return None

    repo = _get_repo_object(client, repo_name)
    if not repo: return None

    try:
        print(f"ℹ️ Attempting to create Pull Request from '{head_branch}' to '{base_branch}' in '{repo_name}'...")
        pr = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
        print(f"✅ Pull Request created successfully: {pr.html_url}")
        return pr.html_url
    except GithubException as e:
        print(f"❌ GitHub API error creating Pull Request from '{head_branch}' to '{base_branch}' in '{repo_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error creating GitHub Pull Request: {type(e).__name__} - {e}")
        return None