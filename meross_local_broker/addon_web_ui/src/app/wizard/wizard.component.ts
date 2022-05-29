import { Component, OnInit, ViewChild } from '@angular/core';
import { MatStepper } from '@angular/material/stepper';

@Component({
  selector: 'app-wizard',
  templateUrl: './wizard.component.html',
  styleUrls: ['./wizard.component.scss'],
})
export class WizardComponent implements OnInit {
  @ViewChild('stepper') stepper!: MatStepper;

  loginVerified: boolean = true;

  constructor() {}

  ngOnInit(): void {}
}
