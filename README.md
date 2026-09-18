# Dog Breed Picker

A small demo web app with the look and feel of a traditional AI chat. You upload a
photo of yourself, and an AI model suggests the dog breed that matches your vibe.

Built with **FastAPI** + vanilla JS, running on **Azure App Service**, powered by a
vision model on **Microsoft Foundry**, and deployed through **GitHub Actions**.

> This is a lighthearted demo, not a serious classifier. The model is prompted to react
> to the mood and style of a photo, and is explicitly instructed never to infer identity,
> age, ethnicity, or health.

**Live app:** https://dog-breed-picker.azurewebsites.net

---

## How to use it

1. Open the app.
2. Click the attach button in the composer and pick a photo.
3. Optionally type a message (for example "I live in a small flat and work long hours") —
   it is sent to the model along with the image and genuinely changes the answer.
4. Hit send. The assistant replies with a breed and a short explanation.

---

## Architecture

```
Browser (static HTML/CSS/JS chat UI)
  │  POST /api/recommend   (multipart: image + optional message)
  ▼
FastAPI on Azure App Service (Linux, Python 3.12, B1)
  │  system-assigned managed identity
  │  role: Cognitive Services OpenAI User
  ▼
Microsoft Foundry — f-local-resource / gpt-5.4-mini (vision)
```

There are **no API keys anywhere**. The app authenticates to Foundry with
`DefaultAzureCredential`, which resolves to the App Service managed identity in Azure
and to your `az login` session when running locally.

### Azure resources

| Resource | Name | Resource group |
| --- | --- | --- |
| App Service plan (Linux B1) | `asp-dog-breed-picker` | `rg-dog-breed-picker` |
| Web app (Python 3.12) | `dog-breed-picker` | `rg-dog-breed-picker` |
| Foundry account (**pre-existing**) | `f-local-resource` | `rg-foundry-local` |

Everything except the Foundry account is described in [`infra/`](infra/) as Bicep.

---

## Project layout

```
app/
  main.py              FastAPI app: routes, validation, lifespan
  recommender.py       StubRecommender + FoundryRecommender behind one Protocol
  config.py            Environment-driven settings
static/
  index.html           Chat shell
  styles.css           Chat styling
  app.js               Composer, image preview, typing indicator, API calls
tests/
  test_api.py          API-level tests
  test_recommender.py  FoundryRecommender tests (mocked client)
infra/
  main.bicep           Plan, web app, settings, managed identity
  foundry-role.bicep   Cross-resource-group role assignment
.github/workflows/
  ci-cd.yml            Test on PRs, deploy on main
```

---

## Running locally

Requires Python 3.12 and the Azure CLI.

```powershell
git clone https://github.com/juantoser/dog-breed-picker.git
cd dog-breed-picker

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/.

By default this runs in **stub mode** — no Azure needed, deterministic fake
recommendations. Great for working on the UI.

### Running against the real model

```powershell
az login

$env:RECOMMENDER_MODE   = "foundry"
$env:FOUNDRY_ENDPOINT   = "https://f-local-resource.cognitiveservices.azure.com/"
$env:FOUNDRY_DEPLOYMENT = "gpt-5.4-mini"

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Your Azure account needs the **Cognitive Services OpenAI User** role on
`f-local-resource`. You can also put these values in a local `.env` file, which is
gitignored.

---

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `RECOMMENDER_MODE` | `stub` | `stub` or `foundry` |
| `FOUNDRY_ENDPOINT` | — | Foundry account endpoint |
| `FOUNDRY_DEPLOYMENT` | — | Model deployment name |
| `FOUNDRY_API_VERSION` | `2024-10-21` | Azure OpenAI API version |
| `FOUNDRY_MAX_TOKENS` | `2000` | Response token cap |

Switch the deployed app between modes without redeploying:

```bash
az webapp config appsettings set -n dog-breed-picker -g rg-dog-breed-picker \
  --settings RECOMMENDER_MODE=stub
```

---

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Chat UI |
| `GET` | `/api/health` | `{"status":"ok"}` |
| `POST` | `/api/recommend` | multipart `image` (required, <= 5 MB) + `message` (optional) |

```json
{
  "breed": "Labrador Retriever",
  "reason": "You give off sunny, energetic beach-day vibes...",
  "confidence": 0.96,
  "source": "foundry"
}
```

Errors: `400` for a non-image or oversized upload, `502` if the recommender is unavailable.

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The Foundry tests mock the model client, so the suite runs offline and needs no Azure
access. CI runs exactly this on every pull request.

---

## CI/CD

[`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml):

- **Pull requests** -> install dependencies and run pytest.
- **Push to `main`** -> run tests, build a zip, deploy to App Service, then poll
  `/api/health` until it returns 200.

Authentication uses **OIDC federated credentials** — no publish profile or secret
password is stored in the repo. The workflow needs these repo secrets:

| Secret | Meaning |
| --- | --- |
| `AZURE_CLIENT_ID` | App registration client ID |
| `AZURE_TENANT_ID` | Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |

> **Note on federated credential subjects.** This repo's OIDC tokens use GitHub's
> immutable-ID subject format (`repo:owner@<id>/repo@<id>:...`). Federated credentials
> are registered for both the readable and immutable forms of `ref:refs/heads/main`,
> `pull_request`, and `environment:production`. If you fork or recreate the repo, the
> numeric IDs change and you must register new credentials to match.

---

## Deploying infrastructure from scratch

```bash
az group create -n rg-dog-breed-picker -l swedencentral

az deployment group create \
  -g rg-dog-breed-picker \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

This creates the plan, web app, managed identity, app settings, and the role assignment
on the existing Foundry account. It does **not** create the Foundry account itself.

---

## Continuing development

A few natural next steps for this demo:

- **Multi-turn chat.** The API is stateless today; each upload is independent. Add a
  conversation history so follow-up questions work.
- **Streaming responses.** Stream tokens to the UI instead of waiting for the full reply.
- **Richer output.** Ask the model for a couple of runner-up breeds, or return a short
  care-requirements summary alongside the pick.
- **Image handling.** Downscale large images client-side before upload to cut latency
  and token cost.
- **Harden for real use.** Add rate limiting, Application Insights, and a staging slot
  so deployments swap rather than restart.
- **Cost control.** The B1 plan runs roughly $13/month. Scale down or stop the app when
  it is not being demoed.

### Workflow

Work on a branch, open a PR, let CI run, then merge. Merging to `main` deploys
automatically — there is no manual deployment step.

```powershell
git checkout -b my-change
# ...edit, then:
.\.venv\Scripts\python.exe -m pytest
git commit -am "Describe the change"
git push -u origin my-change
gh pr create
```

Keep new recommender implementations behind the `Recommender` protocol in
`app/recommender.py` so `RECOMMENDER_MODE` stays the single switch between them.
