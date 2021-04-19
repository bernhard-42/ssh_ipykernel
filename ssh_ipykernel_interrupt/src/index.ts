import { IDisposable, DisposableDelegate } from '@lumino/disposable';
import { ToolbarButton, showErrorMessage, ISessionContext } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection } from '@jupyterlab/services';
import { DocumentRegistry } from '@jupyterlab/docregistry';
import { NotebookPanel, INotebookModel } from '@jupyterlab/notebook';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker } from '@jupyterlab/notebook';
import { runningIcon } from '@jupyterlab/ui-components';
import { ILabShell } from '@jupyterlab/application';

class InterruptButtonExtension implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel> {
  private _kernel_id: string;
  private _kernel_name: string;
  private _button: ToolbarButton;

  set kernel_id(id: string) {
    this._kernel_id = id
  }

  set kernel_name(name: string) {
    this._kernel_name = name
  }

  createNew(panel: NotebookPanel, context: DocumentRegistry.IContext<INotebookModel>): IDisposable {

    let interrupt = () => {
      console.info('InterruptButtonExtension: Interrupt clicked (kernel: ' + this._kernel_name + ')');
      if (this._kernel_name.substring(0, 3) === "SSH") {
        InterruptRequest.interrupt({ id: this._kernel_id })
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
    panel.toolbar.insertItem(7, 'remoteInterrupt', this._button);

    return new DisposableDelegate(() => {
      this._button.dispose();
    });
  }
}

namespace InterruptRequest {
  const SERVER_CONNECTION_SETTINGS = ServerConnection.makeSettings();

  export interface IDbStatusRequestResult {
    status: string;
  }

  async function request(command: string, id: string) {
    console.info("Ssh-ipykernel: InterruptRequest - Requesting interrupt for id", id)
    var url = URLExt.join(SERVER_CONNECTION_SETTINGS.baseUrl, command);
    url = url + "?id=" + id;

    return ServerConnection.makeRequest(url, {}, SERVER_CONNECTION_SETTINGS);
  }

  export async function interrupt({ id }: { id: string }) {
    const response = await request("interrupt", id);
    if (response.ok) {
      var result = await response.json();
      if (result["code"] == 0) {
        console.info("Ssh-ipykernel: InterruptRequest = Success")
      } else {
        console.error("Ssh-ipykernel: InterruptRequest = Error", result)
      }
    } else {
      console.error("Ssh-ipykernel: Interrupt response = Error", response)
    }
  }
}


class RemoteSSH {

  private _extension: InterruptButtonExtension;
  private _notebookTracker: INotebookTracker;

  constructor(extension: InterruptButtonExtension, notebookTracker: INotebookTracker, labShell: ILabShell) {
    this._extension = extension;
    this._notebookTracker = notebookTracker

    labShell.restored.then(
      (layout) => {
        // notebookTracker.currentWidget might be wrong after new start or browser refresh with more 
        // than 1 open tab. Hence loop through all open tabs to find the visble one
        this._notebookTracker.forEach((notebookPanel: NotebookPanel) => {
          if (notebookPanel.isVisible) {
            console.debug("Ssh-ipykernel: select open notebook")
            this.update(1, notebookPanel.sessionContext)
          }
        })

        // When a new tab gets selected, update the kernel id
        this._notebookTracker.currentChanged.connect((sender: INotebookTracker, notebookPanel: NotebookPanel) => {
          console.debug("Ssh-ipykernel: selected notebook changed")
          this.update(2)
        })

        // When a kernel gets strted, restarted or stopped, update the kernel id
        labShell.currentChanged.connect((_, change) => {
          const { oldValue, newValue } = change;
          if (oldValue) {
            var context = (oldValue as NotebookPanel).sessionContext
            context.connectionStatusChanged.disconnect(this.onConnectionStatusChange)
          }
          if (newValue) {
            var context = (newValue as NotebookPanel).sessionContext
            context.connectionStatusChanged.connect(this.onConnectionStatusChange, this)
          }
        })
      }
    )
  }

  onConnectionStatusChange(context: ISessionContext, change: any) {
    console.debug("Ssh-ipykernel: kernel state changed " + change)
    if (change == "disconnected") {
      this.cleanup()
    } else if (change == "connected") {
      this.update(3)
    }
  }

  cleanup() {
    console.info("Ssh-ipykernel: cleanup")
    this._extension.kernel_id = ""
    this._extension.kernel_name = ""
  }

  update(sender: number, context: ISessionContext = null) {
    if (!context) {
      var context = this._notebookTracker.currentWidget.sessionContext;
    }
    context.ready.then(() => {
      // console.debug("Ssh-ipykernel: update context", context);
      if (context.session) {
        var id = context.session.kernel.id
        var name = context.kernelDisplayName
        var path = context.session.path
        console.info("Ssh-ipykernel: update('" + sender + "'): '" + name + "', '" + id + "', '" + path + "'")
        this._extension.kernel_id = id
        this._extension.kernel_name = name
      } else {
        this.cleanup()
      }
    }).catch((reason) => {
      console.error("Ssh-ipykernel: update error ", reason);
      this.cleanup()
    })
  }
}

/**
 * Initialization data for the interrupt-ipykernel-extension extension.
 */

function activate(app: JupyterFrontEnd, notebookTracker: INotebookTracker, labShell: ILabShell): void {
  let buttonExtension = new InterruptButtonExtension();
  app.docRegistry.addWidgetExtension('Notebook', buttonExtension);
  new RemoteSSH(buttonExtension, notebookTracker, labShell)
  console.log("ssh_ipykernel interrupt extension actived")
}

const extension: JupyterFrontEndPlugin<void> = {
  id: 'interrupt-ipykernel-extension',
  requires: [INotebookTracker, ILabShell],
  autoStart: true,
  activate
};

export default extension;
