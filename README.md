# KubeSol: SQL-like Interface for Kubernetes

KubeSol is a modern, extensible command-line tool that provides an SQL-like interface for managing Kubernetes resources and executing data processing scripts. Built with a plugin architecture, KubeSol bridges the gap between familiar SQL syntax and complex Kubernetes operations.

## 🚀 Key Features

### **SQL-like Command Syntax**
Manage Kubernetes resources using familiar SQL verbs like `CREATE`, `DELETE`, `UPDATE`, `GET`, `LIST`, and `EXECUTE`.

### **Plugin Architecture**
- **Modular Design:** Core functionality organized into plugins (Resource, Script, Project)
- **Extensible:** Easy to add new resource types and operations
- **Maintainable:** Clean separation of concerns with dedicated plugin interfaces

### **Project & Environment Management**
- **Project Lifecycle:** Create, manage, and organize Kubernetes projects
- **Environment Dependencies:** Support for environment dependency chains (dev → staging → prod)
- **GitHub Integration:** Automatic repository and branch creation for project environments
- **Environment Context:** Switch between project environments seamlessly

### **Resource Management**
- **Secrets:** Create, update, and manage Kubernetes Secrets
- **ConfigMaps:** Handle configuration data and script parameters
- **Parameters:** Simplified key-value storage (implemented as Secrets)

### **Advanced Script Management**
- **Multi-language Support:** Python, PySpark, and SQL Spark scripts
- **Flexible Execution:** Kubernetes Jobs and Spark Operator engines
- **Smart Parameterization:** Inline arguments or ConfigMap-based parameters
- **Secure Mounting:** Mount secrets and configurations into script environments
- **Code Sources:** Inline code or load from local files

### **Modern Architecture**
- **Dynamic Parser:** Grammar composition from plugins
- **Context Management:** Project and environment-aware operations
- **Interactive Shell:** Rich command-line interface with multi-line support

## 📋 Requirements

- **Python 3.9+**
- **Kubernetes cluster** (local or remote)
- **kubectl** configured and accessible
- **Dependencies:** `kubernetes`, `lark`, `PyGithub`

### Optional
- **Docker** and **KinD** for local development
- **GitHub token** for repository integration

## 🛠️ Installation & Setup

### 1. Clone and Install
```bash
git clone <repository_url>
cd SOL
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install kubernetes lark PyGithub
```

### 2. Configure Kubernetes Access
Ensure your `kubeconfig` is properly configured:
```bash
kubectl cluster-info
```

For local development with KinD:
```bash
kind create cluster --name kubesol-dev
```

### 3. GitHub Integration (Optional)
For project management with GitHub integration:
```bash
# Create a GitHub personal access token and add it as a Kubernetes secret
kubectl create secret generic kubesol-github-token --from-literal=token=<your-github-token>
```

## 🚀 Quick Start

### Start KubeSol
```bash
# Legacy system (stable)
python -m kubeSol.main

# Plugin system (latest features)
python -m kubeSol.main_plugin_system
```

### Basic Project Management
```sql
-- Create a new data project
CREATE PROJECT mydata;

-- Create development environment
CREATE ENV dev FOR PROJECT mydata;

-- Create staging environment that depends on dev
CREATE ENV staging FOR PROJECT mydata DEPENDS ON dev;

-- Switch to project context
USE PROJECT mydata ENV dev;

-- List all projects
LIST PROJECTS;
```

### Resource Management
```sql
-- Create configuration
CREATE CONFIGMAP app_config WITH 
    database_url="postgresql://localhost:5432/mydb",
    api_timeout="30";

-- Create secrets
CREATE SECRET db_credentials WITH 
    username="admin",
    password="secure_password";

-- Create parameters for scripts
CREATE PARAMETER script_params WITH 
    batch_size="1000",
    output_format="parquet";
```

### Script Management
```sql
-- Create a Python data processing script
CREATE SCRIPT data_processor TYPE PYTHON ENGINE K8S_JOB WITH
    CODE="
import pandas as pd
import os

# Get parameters
batch_size = int(os.environ.get('BATCH_SIZE', '100'))
output_format = os.environ.get('OUTPUT_FORMAT', 'csv')

print(f'Processing {batch_size} records in {output_format} format')
# Your data processing logic here
",
    PARAMS_SPEC="BATCH_SIZE,OUTPUT_FORMAT",
    DESCRIPTION="Processes data with configurable batch size and format";

-- Create script from file
CREATE SCRIPT etl_pipeline TYPE PYSPARK ENGINE SPARK_OPERATOR WITH
    CODE_FROM_FILE="/path/to/etl_script.py",
    DESCRIPTION="ETL pipeline for data warehouse";

-- List scripts
LIST SCRIPTS;

-- Get script details
GET SCRIPT data_processor;
```

### Script Execution
```sql
-- Execute with inline parameters
EXECUTE SCRIPT data_processor WITH ARGS (
    BATCH_SIZE="500",
    OUTPUT_FORMAT="parquet"
);

-- Execute with parameters from ConfigMap
EXECUTE SCRIPT data_processor 
    WITH PARAMS_FROM_CONFIGMAP script_params
    WITH SECRET db_credentials KEY "username" AS "/etc/db/username"
    WITH SECRET db_credentials KEY "password" AS "/etc/db/password";

-- Complex execution with multiple sources
EXECUTE SCRIPT etl_pipeline
    WITH ARGS (JOB_ID="daily_etl_001")
    WITH PARAMS_FROM_CONFIGMAP etl_config KEY_PREFIX "spark_"
    WITH SECRET aws_credentials KEY "access_key" AS "/etc/aws/access_key"
    WITH SECRET aws_credentials KEY "secret_key" AS "/etc/aws/secret_key";
```

## 📚 Command Reference

### Project Commands
```sql
CREATE PROJECT <name>                          -- Create new project
LIST PROJECTS                                  -- List all projects  
GET PROJECT <name>                            -- Get project details
GET THIS PROJECT                              -- Get current project details
UPDATE PROJECT <old_name> TO <new_name>      -- Rename project
DROP PROJECT <name>                          -- Delete project
```

### Environment Commands
```sql
CREATE ENV <name> [FOR PROJECT <project>] [DEPENDS ON <env>]  -- Create environment
DROP ENV <name> [FOR PROJECT <project>]                       -- Delete environment
USE PROJECT <project> ENV <env>                               -- Switch context
```

### Resource Commands
```sql
CREATE {SECRET|CONFIGMAP|PARAMETER} <name> WITH <fields>      -- Create resource
UPDATE {SECRET|CONFIGMAP|PARAMETER} <name> WITH <fields>      -- Update resource  
DELETE {SECRET|CONFIGMAP|PARAMETER} <name>                    -- Delete resource
```

### Script Commands
```sql
CREATE SCRIPT <name> TYPE {PYTHON|PYSPARK|SQL_SPARK} [ENGINE {K8S_JOB|SPARK_OPERATOR}] WITH <fields>
UPDATE SCRIPT <name> SET <fields>             -- Update script
DELETE SCRIPT <name>                          -- Delete script
LIST SCRIPTS                                  -- List all scripts
GET SCRIPT <name>                            -- Get script details
EXECUTE SCRIPT <name> [WITH <clauses>]       -- Execute script
```

## 🏗️ Architecture

### Plugin System
```
kubeSol/
├── core/
│   ├── plugin_system/          # Plugin infrastructure
│   ├── parser/                 # Dynamic parser
│   ├── executor/               # Command execution
│   └── context/                # Context management
├── plugins/
│   └── core/
│       ├── resource_plugin.py  # Resource management
│       ├── script_plugin.py    # Script operations  
│       └── project_plugin.py   # Project/environment management
├── engine/                     # Kubernetes operations
├── projects/                   # Project management
└── parser/                     # Legacy parser (compatibility)
```

### Key Components
- **PluginManager:** Discovers, loads, and manages plugins
- **DynamicParser:** Composes grammar from plugins and parses commands
- **DynamicExecutor:** Dispatches commands to appropriate plugin handlers
- **Context:** Manages current project and environment state

## 🔧 Configuration

### Environment Variables
```bash
export KUBESOL_DEFAULT_NAMESPACE=default
export KUBESOL_GITHUB_ORG=your-github-org
export KUBESOL_PROJECT_PREFIX=kubesol-project-
```

### GitHub Integration
Configure GitHub token for automatic repository creation:
```bash
kubectl create secret generic kubesol-github-token \
  --from-literal=token=ghp_your_token_here
```

## 🧪 Testing

```bash
# Test legacy system (baseline)
python test_legacy_system.py

# Test plugin system compatibility
python test_plugin_compatibility.py

# Run specific plugin tests
python -m pytest tests/ -v
```

## 🔍 Development

### Adding New Plugins
1. Create plugin class inheriting from appropriate base interface
2. Implement required methods: `get_grammar_rules()`, `get_command_handlers()`, etc.
3. Register plugin with PluginManager
4. Add tests for new functionality

### Grammar Development
Grammar rules are composed from plugins. Each plugin contributes:
- **Grammar Rules:** Lark syntax definitions
- **Transformer Methods:** Parse tree to command object conversion
- **Command Handlers:** Execution logic
- **Constants:** Shared values and configurations

## 🐛 Troubleshooting

### Common Issues
1. **"No plugins loaded"** - Ensure plugins are registered before loading
2. **Parser errors** - Check grammar rule conflicts between plugins
3. **Kubernetes connection** - Verify kubeconfig and cluster access
4. **GitHub integration** - Check token permissions and secret creation

### Debug Mode
```bash
export KUBESOL_DEBUG=1
python -m kubeSol.main_plugin_system
```

## 🛣️ Roadmap

### Current Focus
- ✅ Plugin architecture implementation
- ✅ Environment dependency management
- ✅ GitHub integration for projects
- 🔄 Enhanced error handling and validation

### Future Plans
- **Multi-cluster Support:** Work with multiple Kubernetes clusters
- **Advanced Script Types:** Support for more languages and frameworks
- **Resource Templates:** Reusable resource configurations
- **Workflow Orchestration:** Complex multi-step data pipelines
- **Web Interface:** Browser-based management console
- **Marketplace:** Community plugin repository

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
git clone <your-fork>
cd SOL
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues:** GitHub Issues for bug reports and feature requests
- **Discussions:** GitHub Discussions for questions and community support
- **Documentation:** See `/docs` folder for detailed documentation

---

**KubeSol** - Making Kubernetes data operations as simple as SQL queries.