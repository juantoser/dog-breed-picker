# Infrastructure

Bicep templates describing the Azure resources for this demo.

## Resources

| Resource | Name | Notes |
| --- | --- | --- |
| Resource group | `rg-dog-breed-picker` | Sweden Central |
| App Service plan | `asp-dog-breed-picker` | Linux, B1 |
| Web app | `dog-breed-picker` | Python 3.12, system-assigned managed identity |
| Foundry account | `f-local-resource` | **Existing**, in `rg-foundry-local`. Referenced, never created. |

The web app's managed identity is granted **Cognitive Services OpenAI User** on the
Foundry account so the app can call the `gpt-5.4-mini` deployment without any API key.

## Files

- `main.bicep` — plan, web app, app settings, managed identity, role assignment module
- `foundry-role.bicep` — cross-resource-group role assignment on the Foundry account
- `main.parameters.json` — default parameter values

## Deploy

```bash
az group create -n rg-dog-breed-picker -l swedencentral

az deployment group create \
  -g rg-dog-breed-picker \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

Validate without deploying:

```bash
az deployment group validate \
  -g rg-dog-breed-picker \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

## App settings

| Setting | Value | Purpose |
| --- | --- | --- |
| `FOUNDRY_ENDPOINT` | `https://f-local-resource.cognitiveservices.azure.com/` | Foundry endpoint |
| `FOUNDRY_DEPLOYMENT` | `gpt-5.4-mini` | Model deployment name |
| `RECOMMENDER_MODE` | `stub` \| `foundry` | Which recommender implementation to use |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Build pip dependencies on deploy |

Flip `RECOMMENDER_MODE` to `foundry` to switch from the stubbed recommender to real
model-backed recommendations.
