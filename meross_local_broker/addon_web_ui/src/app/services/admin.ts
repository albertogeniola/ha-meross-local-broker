import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Device, DeviceOnlineStatus } from '@app/model/device';
import { Event } from '@app/model/event';
import { User } from '@app/model/user';
import { Configuration } from '@app/model/configuration';
import { SubdeviceStore } from '@app/providers/subdevice';
import { ServiceStatus } from '@app/model/service';
import { Subdevice } from '@app/model/subdevice';
import { environment } from '@env/environment';
import { Observable, of } from 'rxjs';
import { catchError, tap, map } from 'rxjs/operators';
import { MatSnackBar } from '@angular/material/snack-bar';

/**
 * Interface for ADMIN apis
 */
@Injectable({
  providedIn: 'root',
})
export class AdminService {
  constructor(private http: HttpClient, private snackBar: MatSnackBar) {}

  /**
   * Handle Http operation that failed.
   * Let the app continue.
   * @param operation - name of the operation that failed
   * @param result - optional value to return as the observable result
   */
  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {
      console.error(error); // log to console instead
      let message: string = 'An error occurred.';

      // Check if an error is available from the data
      let data = error.error;
      if ('info' in data) {
        message = 'Error occurred: ' + data.info;
      }

      // Parse the HTTP result message
      this.snackBar.open(message, 'Dismiss', { duration: 2000 });
      return of(result as T);
    };
  }

  updateDevice(uuid: string, devicePatch: any): Observable<Device> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .put<any>(environment.backend + '/_admin_/devices/' + uuid, devicePatch, { headers })
      .pipe(
        map((device) => {
          // Convert date
          device.last_seen_time = new Date(device.last_seen_time);
          return device as Device;
        }, catchError(this.handleError<Device>('updateDevice', null)))
      );
  }

  listDevices(): Observable<Device[]> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .get<any[]>(environment.backend + '/_admin_/devices', { headers })
      .pipe(
        map((devices) =>
          devices.map((device) => {
            // Convert date
            device.last_seen_time = new Date(device.last_seen_time);
            return device as Device;
          })
        ),
        catchError(this.handleError<Device[]>('listDevices', []))
      );
  }

  listSubdevices(): Observable<Subdevice[]> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .get<Subdevice[]>(environment.backend + '/_admin_/subdevices', { headers })
      .pipe(catchError(this.handleError<any[]>('listSubdevices', [])));
  }

  listServices(): Observable<ServiceStatus[]> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .get<ServiceStatus[]>(environment.backend + '/_admin_/services', { headers })
      .pipe(catchError(this.handleError<any[]>('listServices', [])));
  }

  getServiceLog(serviceName: string): Observable<string[]> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .get<string[]>(environment.backend + '/_admin_/services/' + serviceName + '/log', { headers })
      .pipe(catchError(this.handleError('getServiceLog', [])));
  }

  getConfiguration(): Observable<Configuration | null> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .get<User | null>(environment.backend + '/_admin_/configuration', { headers })
      .pipe(catchError(this.handleError('getConfiguration', null)));
  }

  updateConfiguration(email: string, password: string, enableMerossLink: boolean): Observable<Configuration> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    var data = {
      email: email,
      password: password,
      enableMerossLink: enableMerossLink,
    };

    return this.http
      .put<User | null>(environment.backend + '/_admin_/configuration', data, { headers })
      .pipe(catchError(this.handleError('updateConfiguration', null)));
  }

  // TODO: pass query string parameters
  getEvents(fromTimestamp?: Date, toTimestamp?: Date, limit?: number): Observable<Event[]> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    let params = new HttpParams();
    if (fromTimestamp != null) {
      params.append('fromTimestamp', '' + fromTimestamp.getTime());
    }
    if (toTimestamp != null) {
      params.append('toTimestamp', '' + toTimestamp.getTime());
    }
    if (limit != null) {
      params.append('limit', '' + limit);
    }
    return this.http
      .get<Event[]>(environment.backend + '/_admin_/events', { headers })
      .pipe(catchError(this.handleError('getEvents', null)));
  }

  private executeServiceCommand(serviceName: string, command: string): Observable<boolean> {
    var headers = new HttpHeaders();
    headers.append('Content-Type', 'application/json; charset=utf-8');
    return this.http
      .post<boolean>(
        environment.backend + '/_admin_/services/' + serviceName + '/execute/' + command.toUpperCase(),
        null,
        { headers }
      )
      .pipe(catchError(this.handleError('executeServiceCommand', null)));
  }

  stopService(serviceName: string): Observable<boolean> {
    return this.executeServiceCommand(serviceName, 'STOP');
  }

  startService(serviceName: string): Observable<boolean> {
    return this.executeServiceCommand(serviceName, 'START');
  }

  restartService(serviceName: string): Observable<boolean> {
    return this.executeServiceCommand(serviceName, 'RESTART');
  }
}
