# History

## 1.0.0 (2020-05-07)

* Added an extension to send sigint to the reote kernel via ssh (needed for Windows)
* Added Windows support (for OpoenSSH)
* Added a call to a kernel_customize function for sub classes to inject customizations for the kernel

## 0.1.0 (2019-09-01)

* First release on github

## 0.9.0 (2019-09-03)

* Restructured pxssh calls
* Rewrote keeping alive routine
* Stabilized error detection (cluster not reachable, VPN cut, ipykernel missing)

## 0.9.2 (2019-09-20)

* Added code to call ssh_ipykernel as a module to add a kernel
* Added doc strings to all classes and methods

## 0.9.3 (2019-09-20)

* Fixed argument error for env variables in ssh_ipykernel.manage
