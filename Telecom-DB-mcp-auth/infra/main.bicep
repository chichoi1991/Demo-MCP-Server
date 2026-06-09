targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param telecomDbMcpAuthPythonExists bool

@description('Id of the user or app to assign application roles')
param principalId string

@description('Entra ID tenant ID for Easy Auth (issuer). Required when entraEasyAuthEnabled is true.')
param entraTenantId string = ''

@description('Entra ID application (client) ID for the API app registration. Required when entraEasyAuthEnabled is true.')
param entraClientId string = ''

@description('Allowed audiences for incoming JWTs. Defaults to api://<clientId>.')
param entraAllowedAudiences array = []

@description('Toggle Easy Auth on the Container App. Set to false for an unauthenticated diagnostic deploy.')
param entraEasyAuthEnabled bool = true

var tags = {
  'azd-env-name': environmentName
}

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  scope: rg
  name: 'resources'
  params: {
    location: location
    tags: tags
    principalId: principalId
    telecomDbMcpAuthPythonExists: telecomDbMcpAuthPythonExists
    entraTenantId: entraTenantId
    entraClientId: entraClientId
    entraAllowedAudiences: entraAllowedAudiences
    entraEasyAuthEnabled: entraEasyAuthEnabled
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
output AZURE_RESOURCE_TELECOM_DB_MCP_AUTH_PYTHON_ID string = resources.outputs.AZURE_RESOURCE_TELECOM_DB_MCP_AUTH_PYTHON_ID
