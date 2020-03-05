import { IDisposable, DisposableDelegate } from '@lumino/disposable';
import { ToolbarButton, showErrorMessage } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { Session, ServerConnection } from '@jupyterlab/services';
import { DocumentRegistry } from '@jupyterlab/docregistry';
import { NotebookPanel, INotebookModel } from '@jupyterlab/notebook';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker } from '@jupyterlab/notebook';
import { Kernel } from '@jupyterlab/services';
import { runningIcon } from '@jupyterlab/ui-components';

class InterruptButtonExtension implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel> {
  // private _notebookTracker: INotebookTracker;
  private _host: string = "";
  private _pid: number = -1;
  private _button: ToolbarButton;

  // constructor(notebookTracker: INotebookTracker) {
  //   this._notebookTracker = notebookTracker;
  // }

  createNew(panel: NotebookPanel, context: DocumentRegistry.IContext<INotebookModel>): IDisposable {

    let interrupt = () => {
      console.info('InterruptButtonExtension: Interrupt clicked.');
      // this._notebookTracker.currentWidget.context.sessionContext.session.kernel.interrupt()
      if (this._host != "" && this._pid != -1) {
        InterruptRequest.interrupt({ host: this._host, pid: this._pid })
      } else {
        void showErrorMessage(
          "Error interrupting remote kernel",
          "This is not a remote ssh_ipykernel"
        );
      }
    };

    // Create the toolbar button 
    this._button = new ToolbarButton({
      className: 'interrupt remote kernel',
      icon: runningIcon,
      onClick: interrupt,
      tooltip: 'Interrupt the remote kernel'
    });

    // Add the toolbar button to the notebook
    panel.toolbar.insertItem(7, 'runAllCells', this._button);
    // console.log(this._button, panel)
    // return this._button;
    return new DisposableDelegate(() => {
      this._button.dispose();
    });
  }

  // not working
  // hide() {
  //   console.debug("hide", this)
  //   this._button.hide()
  // }

  // not working
  // show() {
  //   console.debug("show", this)
  //   this._button.show()
  // }

  set pid(pid: number) { this._pid = pid }
  set host(host: string) { this._host = host }
}

namespace InterruptRequest {
  const SERVER_CONNECTION_SETTINGS = ServerConnection.makeSettings();

  export interface IDbStatusRequestResult {
    status: string;
  }

  async function request(command: string, host: string, pid: number) {
    console.info("InterruptRequest: Requesting interrupt for host", host, " and pid", pid)
    var url = URLExt.join(SERVER_CONNECTION_SETTINGS.baseUrl, command);
    url = url + "?pid=" + pid + "&host=" + host;

    return ServerConnection.makeRequest(url, {}, SERVER_CONNECTION_SETTINGS);
  }

  export async function interrupt({ host, pid }: { host: string; pid: number; }) {
    const response = await request("interrupt", host, pid);
    if (response.ok) {
      var result = await response.json();
      if (result["code"] == 0) {
        console.info("InterruptRequest: Success")
      } else {
        console.error("InterruptRequest: Error", result)
      }
    } else {
      console.error("interrupt response: unknown", response)
    }
  }
}

class HostPid {
  host: string;
  pid: number
  constructor(host: string, pid: number) {
    this.host = host
    this.pid = pid
  }
}

interface HostPids {
  [details: string]: HostPid;
}

interface ConnectRegister {
  [details: string]: boolean
}

class RemoteSSH {

  private extension: InterruptButtonExtension;
  private hostpids: HostPids = {};
  private connect_register: ConnectRegister = {};

  constructor(extension: InterruptButtonExtension, notebookTracker: INotebookTracker) {
    this.extension = extension;

    console.debug("Connect to notebookTracker.currentChanged event")
    notebookTracker.currentChanged.connect((slot: any, notebookPanel: NotebookPanel) => {
      console.debug("RemoteSSH:notebookTracker.currentChanged", notebookPanel.id)
      this.update(notebookPanel);

      if (!this.connect_register[notebookPanel.id]) {

        console.debug("Connect to notebookPanel.sessionContext.statusChanged event for", notebookPanel.id)
        notebookPanel.sessionContext.statusChanged.connect((slot: any, status: Kernel.Status) => {
          if (status == "restarting") {
            console.debug("RemoteSSH:notebookPanel.sessionContext.statusChanged:", slot, status)
            this.reset_cache(notebookPanel.id)
            this.update(notebookPanel)
          }
        })

        console.debug("Connect to notebookPanel.sessionContext.kernelChanged event", notebookPanel.id)
        notebookPanel.sessionContext.kernelChanged.connect((slot: any, change: Session.ISessionConnection.IKernelChangedArgs) => {
          if (change.newValue) {
            console.debug("RemoteSSH:notebookPanel.sessionContext.kernelChanged:", change)
            this.reset_cache(notebookPanel.id)
            this.update(notebookPanel)
          }
        })

        this.connect_register[notebookPanel.id] = true
      }
    })
  }

  reset_cache(id: string) {
    this.hostpids[id] = null
  }

  reset_hostpid(id: string) {
    this.extension.host = ""
    this.extension.pid = -1
  }

  update(notebookPanel: NotebookPanel) {
    // console.debug("RemoteSSH:update", notebookPanel, this)
    this.reset_hostpid(notebookPanel.id)

    const context = notebookPanel.sessionContext;
    context.ready.then(
      () => {
        console.debug("RemoteSSH:context.ready")
        const kernel = context.session?.kernel
        if (kernel) {
          setTimeout(() => {
            this.set_host_and_pid(kernel, notebookPanel.id)
          }, 500);
        }
      }
    )
  }

  set_host_and_pid(kernel: Kernel.IKernelConnection, id: string) {
    console.debug("RemoteSSH:set_host_and_pid, cache:", this.hostpids[id])

    if (this.hostpids[id]) {

      this.extension.host = this.hostpids[id].host
      this.extension.pid = this.hostpids[id].pid
      // this.extension.show()
      console.debug("RemoteSSH: Use cached host =", this.hostpids[id].host, ", pid =", this.hostpids[id].pid)

    } else {
      var host = ""
      var pid = -1

      class ReplyData { "text/plain": string; }
      class ReplyContent { data: ReplyData }

      kernel.requestExecute({
        code: "import os",
        user_expressions: { pid: "os.getpid()", host: "os.environ['SSH_IPYKERNEL_HOST']" },
        store_history: false,
        silent: true
      }).done.then(
        (reply: any) => {
          // console.debug("requestExecute -> reply", reply)
          if (reply.content.status == "ok") {
            var ue = reply.content.user_expressions

            try {
              let pid_obj = new ReplyContent();
              Object.assign(pid_obj, ue["pid"]);
              pid = Number(pid_obj.data["text/plain"]);
            } catch (error) {
              pid = -1
              console.error("Could not retrieve remote kernel's pid");
            }

            try {
              var host_obj = new ReplyContent();
              Object.assign(host_obj, ue["host"]);
              host = host_obj.data["text/plain"].slice(1, -1);
            } catch (error) {
              host = ""
              console.debug("Could not retrieve remote kernel's host");
            }

          } else {
            console.error("Could not retrieve remote kernel's pid and host");
          }
          if (pid != -1 && host != "") {
            console.debug("RemoteSSH: Retrieved host =", host, ", pid =", pid)
            this.hostpids[id] = new HostPid(host, pid)
            this.extension.pid = pid
            this.extension.host = host
            // this.extension.show()
          } else {
            console.debug("No remote ssh kernel")

            // this.extension.hide()
          }
        },
        (error: any) => {
          console.error(error);
          // this.extension.hide()
        }
      )
    }
  }
}

/**
 * Initialization data for the interrupt-ipykernel-extension extension.
 */

function activate(app: JupyterFrontEnd, notebookTracker: INotebookTracker): void {
  // let buttonExtension = new InterruptButtonExtension(notebookTracker);
  let buttonExtension = new InterruptButtonExtension();
  app.docRegistry.addWidgetExtension('Notebook', buttonExtension);
  new RemoteSSH(buttonExtension, notebookTracker)
}

const extension: JupyterFrontEndPlugin<void> = {
  id: 'interrupt-ipykernel-extension',
  requires: [INotebookTracker],
  autoStart: true,
  activate
};

export default extension;




// Jupyterlab 1.x
//   if (!notebookTracker.currentWidget) {
//     return;
//   }
//   const notebookContext = notebookTracker.currentWidget.context;
//   notebookContext.ready.then(
//     () => { return notebookTracker.currentWidget.session.ready; },
//     (error) => { console.log("notebookContext.ready", error) }
//   ).then(
//     () => { return notebookTracker.currentWidget.revealed; },
//     (error) => { console.log("notebookTracker.currentWidget.session.ready", error) }
//   ).then(
//     () => { return notebookPanel.session.kernel.ready; },
//     (error) => { console.log("notebookTracker.currentWidget.revealed", error) }
//   ).then(
//     () => {
//       var kernel = notebookPanel.session.kernel
//       console.debug("Current kernel =", kernel)
//       window.ssh_ipykernel = kernel;
//       buttonExtension.get_pid(kernel);
//     },
//     (error) => { console.log("notebookPanel.session.kernel.ready", error) })
