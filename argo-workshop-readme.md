# Argo CD Workshop - Geospatial Edition

A hands-on workshop for deploying geospatial applications using Argo CD and GitOps principles.

## Prerequisites

- [Rancher Desktop](https://rancherdesktop.io/) installed and running (or any local Kubernetes)
- `kubectl` configured and connected to your cluster
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
kubectl get pods -n argocd
```

Wait until all pods show `Running` status.

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

### Step 3: Configure faster sync interval (optional)

By default, Argo CD checks Git every 3 minutes. For the workshop, let's make it faster:

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
│   ├── gdal-api-manual-sync.yaml   # Manual sync example
│   └── gdal-api-auto-sync.yaml     # Auto-sync + self-heal example
└── .github/
    └── workflows/
        └── build-gdal-api.yaml     # CI pipeline
```

### Step 3: Update repository URL

Edit the Argo CD application file and replace the repo URL with your fork:

```bash
sed -i 's/MathewNWSH/YOUR_USERNAME/g' argocd/gdal-api-manual-sync.yaml
sed -i 's/MathewNWSH/YOUR_USERNAME/g' argocd/gdal-api-auto-sync.yaml
```

Commit and push:

```bash
git add .
git commit -m "Update repo URL to my fork"
git push
```

---

## Part III: Sync Scenarios

### Scenario A: Manual Sync

Deploy with manual sync - you control when changes are applied:

```bash
kubectl apply -f argocd/gdal-api-manual-sync.yaml
```

Open Argo CD UI - you should see `gdal-api` application in `OutOfSync` state.

**To sync:**

1. Click on `gdal-api` application
2. Click **SYNC** button
3. Click **SYNCHRONIZE**

### Scenario B: Auto-Sync + Self-Heal

Deploy with automatic sync and self-healing:

```bash
kubectl apply -f argocd/gdal-api-auto-sync.yaml
```

**What's different?**

| Feature                 | Manual Sync         | Auto-Sync |
| ----------------------- | ------------------- | --------- |
| Sync after git push     | Manual (click SYNC) | Automatic |
| Self-heal               | ❌                  | ✅        |
| Prune deleted resources | ❌                  | ✅        |

### Demo: Self-Healing in Action

With auto-sync enabled, try to manually change replicas:

```bash
kubectl scale deployment/gdal-api -n geo --replicas=5
```

Watch what happens:

```bash
kubectl get pods -n geo -w
```

Argo CD will detect the drift and restore to 1 replica (as defined in Git). This is **self-healing** - the cluster always matches Git!

---

## Part IV: Test the API

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

---

## Part V: GitOps Flow - Deploy via Git

Make a change to the deployment and push:

```bash
# Change replicas to 2
sed -i 's/replicas: 1/replicas: 2/' apps/gdal-api/deployment.yaml

git add .
git commit -m "Scale to 2 replicas"
git push
```

Watch Argo CD UI - it will automatically detect the change and deploy 2 pods (if auto-sync is enabled) or show OutOfSync (if manual sync).

---

## Key Concepts Recap

### What Argo CD DOES ✅

- Monitors Git repositories (YAML, Helm, Kustomize)
- Compares desired state (Git) vs actual state (cluster)
- Deploys applications to Kubernetes
- Detects and fixes drift (self-heal)
- Provides rollback capability (via Git)
- Audit trail of all deployments

### What Argo CD does NOT do ❌

- Build Docker images
- Run tests
- Push to container registry
- Monitor container registry (only Git!)
- Is not CI — it is CD only

### The GitOps Flow

```
Code Push → CI (GitHub Actions) → Build Image → Update YAML tag → Argo CD Detects → Deploy
```

### When to use Argo CD?

✅ **Use when:**

- Multiple environments (dev/stage/prod)
- Team > 2 people deploying
- Need audit trail of changes
- Drift is a problem (someone edits cluster manually)

❌ **Don't use when:**

- Single developer, single namespace
- Rapid prototyping (use Tilt instead)
- No Git repo for manifests

---

## Troubleshooting

### Pod stuck in `ErrImagePull`

If using local images, make sure you're using the right Docker context:

```bash
docker context use rancher-desktop
docker build -t gdal-api:local -f apps/gdal-api/Dockerfile apps/gdal-api/
```

### Argo CD shows `OutOfSync` but won't sync

Click **REFRESH** in UI or wait for the sync interval (default 3 min, or 30s if you configured it).

### Cannot access Argo CD UI

Make sure port-forward is running:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Application shows "Unknown" health

The application might still be starting. Wait a moment and click **REFRESH**.

---

## Clean Up

```bash
# Delete the application
kubectl delete -f argocd/gdal-api-auto-sync.yaml
# or
kubectl delete -f argocd/gdal-api-manual-sync.yaml

# Delete namespace
kubectl delete namespace geo

# (Optional) Delete Argo CD
kubectl delete namespace argocd
```

---

## Summary

In this workshop you learned:

1. **How to install Argo CD** on a local Kubernetes cluster
2. **Manual vs Auto-Sync** - when to use each
3. **Self-Healing** - cluster always matches Git
4. **GitOps Flow** - Git as the single source of truth
5. **What Argo CD does and doesn't do** - it's CD, not CI

## Next Steps

- Explore [Argo Workflows](https://argoproj.github.io/argo-workflows/) for data processing pipelines
