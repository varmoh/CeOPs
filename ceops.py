import yaml
from kubernetes import client, config
from typing import Dict

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

# Update Deployment images and environment variables for specified containers
def update_deployment(api_client: client.ApiClient, namespace: str, deployment_name: str, new_images: list, env_vars: list):
    apps_v1 = client.AppsV1Api(api_client)
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    
    updated = False
    
    # Update container images
    for container in deployment.spec.template.spec.containers:
        for new_image in new_images:
            if container.name == new_image['container_name']:
                if container.image != new_image['image']:
                    print(f"Updating container {container.name} from image {container.image} to {new_image['image']}")
                    container.image = new_image['image']
                    updated = True
                else:
                    print(f"Container {container.name} already has the desired image {new_image['image']}")
    
    # Update environment variables
    for container in deployment.spec.template.spec.containers:
        for env_var in env_vars:
            if container.name == env_var['container_name']:
                env_dict = {env.name: env.value for env in container.env}
                updated_env = False
                for new_env in env_var['env']:
                    if env_dict.get(new_env['name']) != new_env['value']:
                        print(f"Updating environment variable {new_env['name']} in container {container.name} from {env_dict.get(new_env['name'])} to {new_env['value']}")
                        # Update environment variable
                        found = False
                        for env in container.env:
                            if env.name == new_env['name']:
                                env.value = new_env['value']
                                found = True
                                updated_env = True
                                break
                        if not found:
                            container.env.append(new_env)
                            updated_env = True
                    else:
                        print(f"Environment variable {new_env['name']} in container {container.name} already has the desired value {new_env['value']}")
                
                if updated_env:
                    updated = True

    if not updated:
        print(f"All specified containers in deployment {deployment_name} already have the desired images and environment variables.")
        return
    
    # Apply the update
    apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
    print(f"Updated deployment {deployment_name} in namespace {namespace} with new images and environment variables.")

# Main function to apply updates across clusters
def main():
    clients = load_cluster_configs('config.yaml')
    update_configs = load_update_configs('update_config.yaml')
    
    new_images = update_configs.get('new_images', [])
    env_vars = update_configs.get('env_vars', [])
    deployment_info = update_configs['deployment_info']
    
    for cluster_name, api_client in clients.items():
        print(f"Processing cluster: {cluster_name}")
        try:
            update_deployment(api_client, **deployment_info, new_images=new_images, env_vars=env_vars)
            print(f"Deployment updated successfully on cluster: {cluster_name}")
        except Exception as e:
            print(f"Error updating cluster {cluster_name}: {e}")

if __name__ == "__main__":
    main()
