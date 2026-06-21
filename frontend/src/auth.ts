import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  CognitoUserSession
} from 'amazon-cognito-identity-js';
import { config } from './config';

let pool: CognitoUserPool | null = null;

export interface LoginResult {
  token?: string;
  challengeUser?: CognitoUser;
  requiredNewPassword?: boolean;
}

function hasCognitoConfig(): boolean {
  return Boolean(config.cognitoUserPoolId && config.cognitoClientId);
}

function getUserPool(): CognitoUserPool {
  if (!hasCognitoConfig()) {
    throw new Error('登入設定尚未完成，請先設定登入服務參數。');
  }
  pool ??= new CognitoUserPool({
    UserPoolId: config.cognitoUserPoolId,
    ClientId: config.cognitoClientId
  });
  return pool;
}

export function login(username: string, password: string): Promise<LoginResult> {
  const user = new CognitoUser({ Username: username, Pool: getUserPool() });
  const authDetails = new AuthenticationDetails({ Username: username, Password: password });
  return new Promise((resolve, reject) => {
    user.authenticateUser(authDetails, {
      onSuccess: (session: CognitoUserSession) => resolve({ token: session.getAccessToken().getJwtToken() }),
      onFailure: reject,
      newPasswordRequired: () => resolve({ challengeUser: user, requiredNewPassword: true })
    });
  });
}

export function completeNewPassword(user: CognitoUser, newPassword: string): Promise<string> {
  return new Promise((resolve, reject) => {
    user.completeNewPasswordChallenge(newPassword, {}, {
      onSuccess: (session: CognitoUserSession) => resolve(session.getAccessToken().getJwtToken()),
      onFailure: reject
    });
  });
}

export function getCurrentToken(): Promise<string | null> {
  if (!hasCognitoConfig()) return Promise.resolve(null);
  const user = getUserPool().getCurrentUser();
  if (!user) return Promise.resolve(null);
  return new Promise((resolve) => {
    user.getSession((error: Error | null, session: CognitoUserSession | null) => {
      if (error || !session?.isValid()) resolve(null);
      else resolve(session.getAccessToken().getJwtToken());
    });
  });
}

export function logout(): void {
  if (!hasCognitoConfig()) return;
  getUserPool().getCurrentUser()?.signOut();
}
