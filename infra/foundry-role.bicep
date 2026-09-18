@description('Name of the existing Foundry (AIServices) account in this resource group.')
param foundryAccountName string

@description('Principal ID of the identity being granted access.')
param principalId string

@description('Built-in role definition GUID to assign.')
param roleDefinitionId string

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryAccountName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccount.id, principalId, roleDefinitionId)
  scope: foundryAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
