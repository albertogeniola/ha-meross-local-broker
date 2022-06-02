export enum DeviceOnlineStatus {
  UNKNOWN = -1,
  NOT_ONLINE = 0,
  ONLINE = 1,
  OFFLINE = 2,
  UPGRADING = 3,
}

export enum BridgeStatus {
  DISCONNECTED = 'Disconnected',
  CONNECTED = 'Connected',
  ERROR = 'Error',
}

export interface DeviceChannel {
  // TODO: define this interface
}

export interface Device {
  readonly mac: string;
  readonly uuid: string;
  readonly deviceType: string;
  readonly subType: string;
  readonly fmwareVersion: string;
  readonly hdwareVersion: string;
  readonly userId: string;
  readonly onlineStatus: DeviceOnlineStatus;
  readonly lastSeenTime: Date;
  readonly localIp: string;
  readonly channels: DeviceChannel[];
  devName: string;
  domain: string;
  reservedDomain: string;
  bridgeStatus: BridgeStatus;
}
