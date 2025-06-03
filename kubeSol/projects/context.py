# kubeSol/projects/context.py
"""
Manages the current operational context (project, environment, namespace) for KubeSol.
An instance of KubeSolContext will be managed by the main shell.
"""
from kubeSol.constants import DEFAULT_NAMESPACE #

class KubeSolContext:
    def __init__(self):
        self.user_project_name: str | None = None
        self.project_id: str | None = None
        self.environment_name: str | None = None
        # current_namespace always reflects the actual Kubernetes namespace to target
        self.current_namespace: str = DEFAULT_NAMESPACE
        self._update_prompt_prefix() # Initialize prompt prefix

    def _update_prompt_prefix(self):
        """Internal helper to update the prompt string component."""
        if self.user_project_name and self.environment_name:
            self.prompt_prefix = f"({self.user_project_name}/{self.environment_name})"
        elif self.current_namespace and self.current_namespace != DEFAULT_NAMESPACE:
            self.prompt_prefix = f"({self.current_namespace})"
        else:
            self.prompt_prefix = f"({DEFAULT_NAMESPACE})"

    def set_project_env_context(self, user_project_name: str, project_id: str, environment_name: str, namespace: str):
        """Sets the full project and environment context."""
        self.user_project_name = user_project_name
        self.project_id = project_id
        self.environment_name = environment_name
        self.current_namespace = namespace
        self._update_prompt_prefix()
        print(f"ℹ️ Context set to Project: '{self.user_project_name}' (ID: {self.project_id}), Environment: '{self.environment_name}' (Namespace: '{self.current_namespace}')")

    def set_namespace_context(self, namespace: str):
        """Sets only the namespace context, attempting to infer project/env if possible (future enhancement) or clearing them."""
        self.current_namespace = namespace
        # If setting to a non-default namespace directly, clear specific project/env names
        # unless we add logic here to resolve them from namespace labels.
        self.user_project_name = None 
        self.project_id = None      
        self.environment_name = None
        if namespace == DEFAULT_NAMESPACE:
             print(f"ℹ️ Current namespace set to default: '{self.current_namespace}'. Project context cleared.")
        else:
            print(f"ℹ️ Current namespace set to '{self.current_namespace}'. Project/environment context needs to be set via 'USE PROJECT' for full functionality.")
        self._update_prompt_prefix()


    def clear_project_context(self):
        """Clears project-specific context, reverting to default namespace."""
        self.user_project_name = None
        self.project_id = None
        self.environment_name = None
        self.current_namespace = DEFAULT_NAMESPACE # Revert to default namespace
        self._update_prompt_prefix()
        print(f"ℹ️ Project context cleared. Current namespace is '{self.current_namespace}'.")

    def get_prompt(self) -> str:
        """Returns the current command prompt string."""
        return f"{self.prompt_prefix} >> "
    
    def get_continuation_prompt(self) -> str:
        """Returns the continuation prompt string for multi-line input."""
        return f"{self.prompt_prefix} ... "

    def is_project_context_active(self) -> bool: # << इंश्योर THIS METHOD EXISTS
        """Checks if a KubeSol project context (ID and name) is currently active."""
        return bool(self.project_id and self.user_project_name)

    def __str__(self):
        if self.user_project_name and self.environment_name:
            return (f"Current Context: Project='{self.user_project_name}' (ID: {self.project_id}), "
                    f"Environment='{self.environment_name}', Namespace='{self.current_namespace}'")
        return f"Current Context: Namespace='{self.current_namespace}' (No specific KubeSol project context active)"