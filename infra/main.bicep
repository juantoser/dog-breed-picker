@description('Name of the web app. Must be globally unique.')
param webAppName string = 'dog-breed-picker'

@description('Name of the App Service plan.')
param appServicePlanName string = 'asp-dog-breed-picker'

@description('Azure region for the resources.')
param location string = resourceGroup().location

@description('Resource group containing the existing Foundry (AIServices) account.')
param foundryResourceGroupName string = 'rg-foundry-local'

@description('Name of the existing Foundry (AIServices) account.')
param foundryAccountName string = 'f-local-resource'

@description('Model deployment name on the Foundry account.')
param foundryDeployment string = 'gpt-5.4-mini'

@description('Which recommender implementation the app should use.')
@allowed([
  'stub'
  'foundry'
])
param recommenderMode string = 'stub'

var foundryEndpoint = 'https://${foundryAccountName}.cognitiveservices.azure.com/'

// Built-in role: Cognitive Services OpenAI User
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'FOUNDRY_ENDPOINT'
          value: foundryEndpoint
        }
        {
          name: 'FOUNDRY_DEPLOYMENT'
          value: foundryDeployment
        }
        {
          name: 'RECOMMENDER_MODE'
          value: recommenderMode
        }
      ]
    }
  }
}

module foundryRoleAssignment 'foundry-role.bicep' = {
  name: 'foundry-role-assignment'
  scope: resourceGroup(foundryResourceGroupName)
  params: {
    foundryAccountName: foundryAccountName
    principalId: webApp.identity.principalId
    roleDefinitionId: openAiUserRoleId
  }
}

output webAppName string = webApp.name
output webAppHostName string = 'https://${webApp.properties.defaultHostName}'
output webAppPrincipalId string = webApp.identity.principalId
