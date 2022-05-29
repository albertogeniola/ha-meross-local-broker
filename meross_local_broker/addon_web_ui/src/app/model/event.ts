export enum DeviceOnlineStatus {
  // General / Uncathegorized
  CONNECT_FAILURE = 'CONNECT_FAILURE',

  // User login
  USER_LOGIN_FAILURE = 'USER_LOGIN_FAILURE',
  USER_LOGIN_SUCCESS = 'USER_LOGIN_SUCCESS',

  // Device events
  DEVICE_CONNECT_FAILURE = 'DEVICE_CONNECT_FAILURE',
  DEVICE_CONNECT_SUCCESS = 'DEVICE_CONNECT_SUCCESS',
  DEVICE_DISCONNECTION = 'DEVICE_DISCONNECTION',

  // Agent login
  AGENT_LOGIN_ATTEMPTED = 'AGENT_LOGIN_ATTEMPTED',

  // Actions
  CONFIGURATION_CHANGE = 'CONFIGURATION_CHANGE',
  SERVICE_START = 'SERVICE_START',
  SERVICE_STOP = 'SERVICE_STOP',
  SERVICE_RESTART = 'SERVICE_RESTART',
}

export interface Event {
  readonly event_id: DeviceOnlineStatus;
  readonly timestamp: Date;
  readonly event_type: string;
  readonly device_uuid: string;
  readonly sub_device_id: string;
  readonly user_id: string;
  readonly details: string;
}
