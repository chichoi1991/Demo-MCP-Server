@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

param telecomDbMcpPythonExists bool

@description('Id of the user or app to assign application roles')
param principalId string

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = uniqueString(subscription().id, resourceGroup().id, location)

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
        principalId: telecomDbMcpPythonIdentity.outputs.principalId
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

module telecomDbMcpPythonIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'telecomDbMcpPythonIdentity'
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}telecom-db-mcp-python-${resourceToken}'
    location: location
  }
}

module telecomDbMcpPythonFetchLatestImage './modules/fetch-container-image.bicep' = {
  name: 'telecomDbMcpPython-fetch-image'
  params: {
    exists: telecomDbMcpPythonExists
    name: 'telecom-db-mcp-python'
  }
}

module telecomDbMcpPython 'br/public:avm/res/app/container-app:0.8.0' = {
  name: 'telecomDbMcpPython'
  params: {
    name: 'telecom-db-mcp-python'
    ingressTargetPort: 3000
    // Scale-out tuning: pre-warm 2 replicas, allow up to 20.
    // Combined with the http scale rule (10 concurrent req / replica) this
    // comfortably absorbs ~100 concurrent callers with headroom.
    scaleMinReplicas: 2
    scaleMaxReplicas: 20
    scaleRules: [
      {
        name: 'http-concurrency'
        http: {
          metadata: {
            concurrentRequests: '10'
          }
        }
      }
    ]
    secrets: {
      secureList: []
    }
    containers: [
      {
        image: telecomDbMcpPythonFetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        name: 'main'
        resources: {
          cpu: json('2.0')
          memory: '4.0Gi'
        }
        env: [
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: monitoring.outputs.applicationInsightsConnectionString
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: telecomDbMcpPythonIdentity.outputs.clientId
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
      userAssignedResourceIds: [telecomDbMcpPythonIdentity.outputs.resourceId]
    }
    registries: [
      {
        server: containerRegistry.outputs.loginServer
        identity: telecomDbMcpPythonIdentity.outputs.resourceId
      }
    ]
    environmentResourceId: containerAppsEnvironment.outputs.resourceId
    location: location
    tags: union(tags, { 'azd-service-name': 'telecom-db-mcp-python' })
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output AZURE_RESOURCE_TELECOM_DB_MCP_PYTHON_ID string = telecomDbMcpPython.outputs.resourceId
