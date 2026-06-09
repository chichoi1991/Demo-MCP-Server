@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

param telecomDbMcpAuthPythonExists bool

@description('Id of the user or app to assign application roles')
param principalId string

@description('Entra ID tenant ID for Easy Auth (issuer).')
param entraTenantId string

@description('Entra ID application (client) ID for the API app registration.')
param entraClientId string

@description('Allowed audiences for incoming JWTs. Defaults to api://<clientId>.')
param entraAllowedAudiences array = []

@description('Toggle Easy Auth on the Container App.')
param entraEasyAuthEnabled bool = true

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = uniqueString(subscription().id, resourceGroup().id, location)

var containerAppName = 'telecom-db-mcp-auth-python'
var defaultAudience = empty(entraClientId) ? '' : 'api://${entraClientId}'
var effectiveAudiences = empty(entraAllowedAudiences) ? [defaultAudience] : entraAllowedAudiences

// Monitor application with Azure Monitor
module monitoring 'br/public:avm/ptn/azd/monitoring:0.1.0' = {
  name: 'monitoring'
  params: {
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: '${abbrs.portalDashboards}${resourceToken}'
    location: location
    tags: tags
  }
}

// Container registry
module containerRegistry 'br/public:avm/res/container-registry/registry:0.1.1' = {
  name: 'registry'
  params: {
    name: '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: tags
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: telecomDbMcpAuthPythonIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId(
          'Microsoft.Authorization/roleDefinitions',
          '7f951dda-4ed3-4680-a7ca-43fe172d538d'
        )
      }
    ]
  }
}

// Container apps environment
module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.4.5' = {
  name: 'container-apps-environment'
  params: {
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    zoneRedundant: false
  }
}

module telecomDbMcpAuthPythonIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'telecomDbMcpAuthPythonIdentity'
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}telecom-db-mcp-auth-python-${resourceToken}'
    location: location
  }
}

module telecomDbMcpAuthPythonFetchLatestImage './modules/fetch-container-image.bicep' = {
  name: 'telecomDbMcpAuthPython-fetch-image'
  params: {
    exists: telecomDbMcpAuthPythonExists
    name: containerAppName
  }
}

module telecomDbMcpAuthPython 'br/public:avm/res/app/container-app:0.8.0' = {
  name: 'telecomDbMcpAuthPython'
  params: {
    name: containerAppName
    ingressTargetPort: 3000
    scaleMinReplicas: 1
    scaleMaxReplicas: 5
    secrets: {
      secureList: []
    }
    containers: [
      {
        image: telecomDbMcpAuthPythonFetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        name: 'main'
        resources: {
          cpu: json('1.0')
          memory: '2.0Gi'
        }
        env: [
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: monitoring.outputs.applicationInsightsConnectionString
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: telecomDbMcpAuthPythonIdentity.outputs.clientId
          }
          {
            name: 'PORT'
            value: '3000'
          }
        ]
      }
    ]
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [telecomDbMcpAuthPythonIdentity.outputs.resourceId]
    }
    registries: [
      {
        server: containerRegistry.outputs.loginServer
        identity: telecomDbMcpAuthPythonIdentity.outputs.resourceId
      }
    ]
    environmentResourceId: containerAppsEnvironment.outputs.resourceId
    location: location
    tags: union(tags, { 'azd-service-name': 'telecom-db-mcp-auth-python' })
  }
}

// ── Easy Auth (Microsoft Entra) ───────────────────────────────────
// Bound as a child of the Container App created by the AVM module.
// Reference the app via 'existing' so we can attach an authConfig child.
resource telecomDbMcpAuthApp 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: containerAppName
}

resource telecomDbMcpAuthEasyAuth 'Microsoft.App/containerApps/authConfigs@2024-03-01' = if (entraEasyAuthEnabled) {
  parent: telecomDbMcpAuthApp
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      // Return 401 (rather than redirect) so MCP/REST clients can handle auth.
      unauthenticatedClientAction: 'Return401'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: entraClientId
          openIdIssuer: 'https://login.microsoftonline.com/${entraTenantId}/v2.0'
        }
        validation: {
          allowedAudiences: effectiveAudiences
        }
      }
    }
  }
  dependsOn: [
    telecomDbMcpAuthPython
  ]
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output AZURE_RESOURCE_TELECOM_DB_MCP_AUTH_PYTHON_ID string = telecomDbMcpAuthPython.outputs.resourceId
output EASY_AUTH_ENABLED bool = entraEasyAuthEnabled
output EASY_AUTH_AUDIENCES array = effectiveAudiences
