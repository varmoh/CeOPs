import yaml
from kubernetes import client, config
from typing import Dict, List, Dict as TypingDict

# Load Kubernetes configurations for each cluster
def load_cluster_configs(config_file: str) -> Dict[str, client.ApiClient]:
    with open(config_file, 'r') as f:
        configs = yaml.safe_load(f)
    
    clients = {}
    for cluster in configs.get('clusters', []):
        name = cluster['name']
        kubeconfig = cluster['kubeconfig']
        
        config.load_kube_config(config_file=kubeconfig)
        api_client = client.ApiClient()
        clients[name] = api_client
    return clients

# Load update configurations from YAML file
def load_update_configs(config_file: str) -> dict:
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

# Compare current and desired state and return a list of changes
def compare_deployment(api_client: client.ApiClient, namespace: str, deployment_name: str, new_images: list, env_vars: list) -> Dict[str, List[str]]:
    apps_v1 = client.AppsV1Api(api_client)
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    
    current_images = {container.name: container.image for container in deployment.spec.template.spec.containers}
    current_env_vars = {container.name: {env.name: env.value for env in container.env} for container in deployment.spec.template.spec.containers}
    
    image_changes = []
    env_changes = []
    
    # Check image updates
    for new_image in new_images:
        if new_image['container_name'] in current_images:
            if current_images[new_image['container_name']] != new_image['image']:
                image_changes.append(f"Image for container {new_image['container_name']} will be updated from {current_images[new_image['container_name']]} to {new_image['image']}")
    
    # Check environment variable updates
    for env_var in env_vars:
        if env_var['container_name'] in current_env_vars:
            current_env = current_env_vars[env_var['container_name']]
            for new_env in env_var['env']:
                if current_env.get(new_env['name']) != new_env['value']:
                    env_changes.append(f"Environment variable {new_env['name']} in container {env_var['container_name']} will be updated from {current_env.get(new_env['name'])} to {new_env['value']}")
    
    return {'image_changes': image_changes, 'env_changes': env_changes}

# Apply Deployment updates for specified containers
def apply_changes(api_client: client.ApiClient, namespace: str, deployment_name: str, new_images: List[Dict], env_vars: List[Dict]):
    apps_v1 = client.AppsV1Api(api_client)
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    
    # Update container images if specified
    if new_images:
        for container in deployment.spec.template.spec.containers:
            for new_image in new_images:
                if container.name == new_image['container_name']:
                    container.image = new_image['image']
    
    # Update environment variables if specified
    if env_vars:
        for container in deployment.spec.template.spec.containers:
            for env_var in env_vars:
                if container.name == env_var['container_name']:
                    env_dict = {env.name: env.value for env in container.env}
                    for new_env in env_var['env']:
                        found = False
                        for env in container.env:
                            if env.name == new_env['name']:
                                env.value = new_env['value']
                                found = True
                                break
                        if not found:
                            container.env.append(new_env)
    
    # Apply the update
    apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
    print(f"Deployment {deployment_name} updated in namespace {namespace}")

# Main function to check, notify, and apply updates across clusters
def main():
    clients = load_cluster_configs('config.yaml')
    update_configs = load_update_configs('update_config.yaml')
    
    new_images = update_configs.get('new_images', [])
    env_vars = update_configs.get('env_vars', [])
    deployment_info = update_configs['deployment_info']
    
    for cluster_name, api_client in clients.items():
        print(f"Processing cluster: {cluster_name}")
        try:
            # Compare and get changes
            changes = compare_deployment(api_client, **deployment_info, new_images=new_images, env_vars=env_vars)
            if not changes['image_changes'] and not changes['env_changes']:
                print("No changes detected")
                continue  # Skip to the next cluster if no changes are detected
            
            # Display and ask for confirmation
            if changes['image_changes']:
                print("Detected image changes:")
                for change in changes['image_changes']:
                    print(change)
                image_confirmation = input("Do you want to apply these image changes? (yes/no): ").strip().lower()
                if image_confirmation == 'yes':
                    apply_changes(api_client, **deployment_info, new_images=new_images, env_vars=[])
                    print(f"Image changes applied successfully on cluster: {cluster_name}")
                else:
                    print(f"Image changes not applied on cluster: {cluster_name}")

            if changes['env_changes']:
                print("Detected environment variable changes:")
                for change in changes['env_changes']:
                    print(change)
                env_confirmation = input("Do you want to apply these environment variable changes? (yes/no): ").strip().lower()
                if env_confirmation == 'yes':
                    apply_changes(api_client, **deployment_info, new_images=[], env_vars=env_vars)
                    print(f"Environment variable changes applied successfully on cluster: {cluster_name}")
                else:
                    print(f"Environment variable changes not applied on cluster: {cluster_name}")
                
        except Exception as e:
            print(f"Error updating cluster {cluster_name}: {e}")

if __name__ == "__main__":
    main()
