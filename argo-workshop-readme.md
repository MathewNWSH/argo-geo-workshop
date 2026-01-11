# Argo CD Workshop - Geospatial Edition

A hands-on workshop for deploying geospatial applications using Argo CD and GitOps principles.

## Prerequisites

- [Rancher Desktop](https://rancherdesktop.io/) installed and running (or any local Kubernetes)
- `kubectl` configured and connected to your cluster
- `helm` installed
- GitHub account
- Git configured locally

### Verify your setup

```bash
kubectl cluster-info
kubectl get nodes
```

You should see your cluster running.

---

## Part I: Deploy Argo CD

### Step 1: Install Argo CD

Create namespace and install Argo CD:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait for pods to be ready:

```bash
kubectl get pods -n argocd -w
```

Press `Ctrl+C` when all pods show `Running` status.

### Step 2: Access Argo CD UI

Get the admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

Save this password!

Start port-forward to access UI:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open browser: https://localhost:8080

- Username: `admin`
- Password: (from command above)

> Note: Browser will warn about certificate - click "Advanced" → "Proceed" to continue.

### Step 3: Configure faster sync (optional)

By default, Argo CD checks Git every 3 minutes. For workshop, let's make it faster:

```bash
kubectl patch configmap argocd-cm -n argocd --type merge -p '{"data":{"timeout.reconciliation":"30s"}}'
kubectl rollout restart deployment argocd-repo-server -n argocd
kubectl rollout restart deployment argocd-application-controller -n argocd
```

### ✅ Part I Complete!

You now have Argo CD running. Keep the port-forward terminal open.

---

## Part II: Deploy GDAL API with GitOps

We'll deploy a FastAPI service that returns GeoTIFF metadata using GDAL.

### Step 1: Fork and clone the repository

1. Fork this repo: https://github.com/MathewNWSH/argo-geo-workshop
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/argo-geo-workshop.git
cd argo-geo-workshop
```

### Step 2: Explore the application

The repository structure:

```
argo-geo-workshop/
├── apps/
│   └── gdal-api/
│       ├── main.py           # FastAPI application
│       ├── Dockerfile        # Container image definition
│       ├── deployment.yaml   # Kubernetes Deployment
│       └── service.yaml      # Kubernetes Service
├── argocd/
│   └── gdal-api-app.yaml     # Argo CD Application definition
└── .github/
    └── workflows/
        └── build-gdal-api.yaml  # CI pipeline
```

### Step 3: Update repository URL

Edit `argocd/gdal-api-app.yaml` and replace the repo URL with your fork:

```yaml
spec:
  source:
    repoURL: https://github.com/YOUR_USERNAME/argo-geo-workshop.git
```

Commit and push:

```bash
git add .
git commit -m "Update repo URL to my fork"
git push
```

### Step 4: Create the Application in Argo CD

```bash
kubectl apply -f argocd/gdal-api-app.yaml
```

Open Argo CD UI - you should see `gdal-api` application in `OutOfSync` state.

### Step 5: Sync the application

In Argo CD UI:

1. Click on `gdal-api` application
2. Click **SYNC** button
3. Click **SYNCHRONIZE**

Watch the deployment progress in the UI.

### Step 6: Test the API

Start port-forward to the service:

```bash
kubectl port-forward -n geo svc/gdal-api 8000:80
```

Test endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Get metadata from a Sentinel-2 COG
curl -X POST http://localhost:8000/gdalinfo \
  -H "Content-Type: application/json" \
  -d '{"url": "/vsicurl/https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/36/Q/WD/2020/7/S2A_36QWD_20200701_0_L2A/B04.tif"}'
```

You should see GeoTIFF metadata (size, CRS, bands, etc.).

### Step 7: Experience GitOps - Auto-sync

Enable auto-sync by updating the Application:

```bash
cat > argocd/gdal-api-app.yaml << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gdal-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/YOUR_USERNAME/argo-geo-workshop.git
    targetRevision: master
    path: apps/gdal-api
  destination:
    server: https://kubernetes.default.svc
    namespace: geo
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
```

> ⚠️ Remember to replace `YOUR_USERNAME` with your GitHub username!

Apply:

```bash
kubectl apply -f argocd/gdal-api-app.yaml
```

### Step 8: Test Self-Healing

Try to manually change replicas:

```bash
kubectl scale deployment/gdal-api -n geo --replicas=5
```

Watch what happens:

```bash
kubectl get pods -n geo -w
```

Argo CD will detect the drift and restore to 1 replica (as defined in Git). This is **self-healing** in action!

### Step 9: Deploy via Git push

Make a change to the deployment:

```bash
# Change replicas to 2
sed -i 's/replicas: 1/replicas: 2/' apps/gdal-api/deployment.yaml

git add .
git commit -m "Scale to 2 replicas"
git push
```

Watch Argo CD UI - it will automatically detect the change and deploy 2 pods.

### ✅ Part II Complete!

You've experienced the full GitOps workflow:

- **Git as source of truth** - changes come from Git, not kubectl
- **Auto-sync** - automatic deployment when Git changes
- **Self-healing** - automatic recovery from manual changes

---

## Key Concepts Recap

### What Argo CD DOES

- Monitors Git repositories
- Compares desired state (Git) vs actual state (cluster)
- Deploys applications to Kubernetes
- Detects and fixes drift (self-heal)
- Provides rollback capability
- Audit trail of all deployments

### What Argo CD DOES NOT do

- Build Docker images
- Run tests
- Push to container registry
- Monitor container registry

### The GitOps Flow

```
Code Push → CI (GitHub Actions) → Build Image → Update YAML → Argo CD Detects → Deploy
```

---

## Troubleshooting

### Pod stuck in `ErrImagePull`

If using local images, make sure you're using the right Docker context:

```bash
docker context use rancher-desktop
docker build -t gdal-api:local -f apps/gdal-api/Dockerfile apps/gdal-api/
```

### Argo CD shows `Unknown` status

Click **REFRESH** in UI or wait for the sync interval.

### Cannot access Argo CD UI

Make sure port-forward is running:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

---

## Clean Up

```bash
# Delete the application
kubectl delete -f argocd/gdal-api-app.yaml

# Delete namespace
kubectl delete namespace geo

# (Optional) Delete Argo CD
kubectl delete namespace argocd
```

---

## Next Steps

- Explore [Argo Workflows](https://argoproj.github.io/argo-workflows/) for CI/CD pipelines
