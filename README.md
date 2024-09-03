# CeOPs
Local central operation tool for k8s management

Currently have added following things that can be managed

- Images version change
- ENV changes


##### Testing on local minikube

Currently all the config files have been set up for local testing

```
kubectl apply -f ./test/test-deployment.yaml
```

Change the `update_config.yaml` as you see fit and run

```
python3 ceops.py
```
