export interface RuntimeConfig {
  apiBaseUrl: string;
  cognitoUserPoolId: string;
  cognitoClientId: string;
}

export const config: RuntimeConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
  cognitoUserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID ?? '',
  cognitoClientId: import.meta.env.VITE_COGNITO_CLIENT_ID ?? ''
};
