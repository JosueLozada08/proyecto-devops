# Guía Completa para Levantar el Proyecto – Proyecto DevOps

## 1. Prerrequisitos
- Python 3.10+
- Docker Desktop
- Git
- Kubernetes local (Minikube o Docker Desktop)
- Argo CD instalado

## 2. Descargar el proyecto
```bash
git clone https://github.com/JosueLozada08/proyecto-devops.git
cd proyecto-devops
```

## 3. Levantar el proyecto localmente
### Crear entorno virtual
```bash
python -m venv venv
```
Windows:
```powershell
.env\Scripts\activate
```
Linux/Mac:
```bash
source venv/bin/activate
```
### Instalar dependencias
```bash
pip install -r requirements.txt
```
### Variable de LaunchDarkly (opcional)
```powershell
[System.Environment]::SetEnvironmentVariable("LAUNCHDARKLY_SDK_KEY", "sdk-xxx", "Process")
```
### Ejecutar API
```bash
uvicorn app.main:app --reload
```
Abrir: http://127.0.0.1:8000/docs

## 4. Levantar con Docker
### Build
```bash
docker build -t api-devops:latest .
```
### Run
```bash
docker run -p 8000:8000 api-devops:latest
```

## 5. Kubernetes
### Aplicar manifiestos
```bash
kubectl apply -f k8s/
```
### Ver pods
```bash
kubectl get pods
```
### Acceder API
```bash
kubectl port-forward svc/api-devops 8000:8000
```

## 6. Argo CD – GitOps
### Instalar Argo CD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```
### Exponer UI
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:80
```
Abrir: http://localhost:8080

### Password inicial
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```
### Registrar repo privado
UI → Settings → Repositories → Connect Repo
URL: https://github.com/JosueLozada08/proyecto-devops.git

### Aplicar Application
```bash
kubectl apply -n argocd -f k8s/argocd-application.yaml
```

## 7. Flujo CI/CD + GitOps
1. Push a main
2. GitHub Actions construye y publica imagen Docker
3. Argo CD sincroniza y despliega

## 8. Comandos útiles
```bash
kubectl get pods
kubectl logs -f <pod>
kubectl delete -f k8s/
```
