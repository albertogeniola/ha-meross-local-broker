import { Component, OnInit, ViewChild } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatStepper } from '@angular/material/stepper';
import { Configuration } from '@app/model/configuration';
import { AdminService } from '@app/services/admin';

@Component({
  selector: 'app-wizard',
  templateUrl: './wizard.component.html',
  styleUrls: ['./wizard.component.scss'],
})
export class WizardComponent implements OnInit {
  @ViewChild('stepper') stepper!: MatStepper;
  public loginVerified: boolean = false;
  public configured: boolean = false;
  private loginEventPoller: number = null;
  private lastTimestamp: Date = null;

  constructor(private adminService: AdminService, private snackBar: MatSnackBar) {}

  ngOnInit(): void {
    this.adminService.getConfiguration().subscribe((conf: Configuration) => {
      this.configured = conf != null;
    });
  }

  onConfigurationUpdate() {
    // When the configuration is updated, proceed to the next
    // section and start the login poller.
    this.stepper.next();
    this.startWaitingForLogin();
  }

  private startWaitingForLogin() {
    // Make sure we do not start another poller
    if (this.loginEventPoller != null) {
      console.error('An interval poller has already been set.');
      return;
    }

    // Reset the loginVerified flag
    this.loginVerified = false;
    this.lastTimestamp = null;
    this.loginEventPoller = window.setInterval(() => {
      if (this.lastTimestamp == null) {
        this.lastTimestamp = new Date();
      }
      let now = new Date();
      this.adminService.getEvents(this.lastTimestamp).subscribe((evts) => {
        console.log(evts);
        // TODO... filter for LOGIN success and clear the timer.
        for (let i = 0; i < evts.length; i++) {
          if (evts[i].eventType == 'USER_LOGIN_SUCCESS') {
            window.clearInterval(this.loginEventPoller);
            console.info('Login success detected: ', evts[i]);
            this.loginVerified = true;
            return;
          } else if (evts[i].eventType == 'USER_LOGIN_FAILURE') {
            console.warn('Login failure detected:', evts[i]);
            this.snackBar.open('A login attempt was detected, but failed due to: ' + evts[i].details, 'Dismiss', {
              duration: 4000,
            });
          }
        }
        this.lastTimestamp = now;
      });
    }, 2000);
  }
}
