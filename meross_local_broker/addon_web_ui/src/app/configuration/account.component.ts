import { Component, OnInit } from '@angular/core';
import { NgxQrcodeElementTypes, NgxQrcodeErrorCorrectionLevels } from '@techiediaries/ngx-qrcode';
import { AdminService } from '@app/services/admin';
import { User } from '@app/model/user';
import { FormBuilder } from '@angular/forms';
import { Validators } from '@angular/forms';
import { Output, EventEmitter } from '@angular/core';
import { Configuration } from '@app/model/configuration';

@Component({
  selector: 'configuration-account',
  templateUrl: './account.component.html',
  styleUrls: ['./account.component.scss'],
})
export class AccountComponent implements OnInit {
  accountForm = this.fb.group({
    email: ['', Validators.required],
    password: ['', Validators.required],
    enableMerossLink: [false],
  });

  @Output() configurationUpdatedEvent = new EventEmitter<string>();

  public hidePassword: boolean = true;
  public processing: boolean = false;

  public elementType = NgxQrcodeElementTypes.IMG;
  public correctionLevel = NgxQrcodeErrorCorrectionLevels.MEDIUM;
  public encodedAccountLoginData: string = null;
  public reconfigure: boolean = false;

  public configuration: Configuration = null;

  constructor(private fb: FormBuilder, private adminService: AdminService) {}

  private loadConfiguration(conf: Configuration | null) {
    if (!conf) {
      this.configuration = null;
      this.reconfigure = true;
    } else {
      // Fetch configured data
      this.configuration = conf;
      this.accountForm.controls.password.setValue(null);
      this.accountForm.controls.email.setValue(conf.email);
      this.accountForm.controls.enableMerossLink.setValue(conf.enableMerossLink);
    }
  }

  ngOnInit(): void {
    this.adminService.getConfiguration().subscribe((configuration: Configuration) => {
      this.loadConfiguration(configuration);
    });
  }

  editConfiguration(reconfigure: boolean): void {
    if (reconfigure) {
      this.adminService.getConfiguration().subscribe(
        (configuration: Configuration) => {
          this.loadConfiguration(configuration);
        },
        (error) => {}
      );
    }
    this.reconfigure = reconfigure;
  }

  onSubmit(): void {
    this.processing = true;
    this.adminService
      .updateConfiguration(
        this.accountForm.controls.email.value,
        this.accountForm.controls.password.value,
        this.accountForm.controls.enableMerossLink.value
      )
      .subscribe((configuration: Configuration) => {
        if (configuration != null) {
          this.loadConfiguration(configuration);
          this.editConfiguration(false);
          this.configurationUpdatedEvent.emit('ACCOUNT_CONFIGURED');
        }
        this.processing = false;
      });
  }
}
