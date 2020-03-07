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
      console.info('InterruptButtonExtension: Interrupt clicked.', this._kernel_name, this._kernel_id);
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
}

namespace InterruptRequest {
  const SERVER_CONNECTION_SETTINGS = ServerConnection.makeSettings();

  export interface IDbStatusRequestResult {
    status: string;
  }

  async function request(command: string, id: string) {
    console.info("InterruptRequest: Requesting interrupt for id", id)
    var url = URLExt.join(SERVER_CONNECTION_SETTINGS.baseUrl, command);
    url = url + "?id=" + id;

    return ServerConnection.makeRequest(url, {}, SERVER_CONNECTION_SETTINGS);
  }

  export async function interrupt({ id }: { id: string }) {
    const response = await request("interrupt", id);
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


class RemoteSSH {

  private _extension: InterruptButtonExtension;

  constructor(extension: InterruptButtonExtension, notebookTracker: INotebookTracker, labShell: ILabShell) {
    this._extension = extension;

    labShell.restored.then((layout) => notebookTracker.currentWidget.sessionContext.ready).then(
      () => {

        console.debug("RemoteSSH: Connect to labShell.currentChanged")
        labShell.currentChanged.connect((_, change) => {
          console.log("labShell.currentChanged", change)
          const { oldValue, newValue } = change;
          if (oldValue) {
            var context = (oldValue as NotebookPanel).sessionContext
            context.connectionStatusChanged.disconnect(this.onConnectionStatusChange)
          }
          if (newValue) {
            var context = (newValue as NotebookPanel).sessionContext
            context.connectionStatusChanged.connect(this.onConnectionStatusChange, this)
            this.update(context)
          }
        })

        var context = notebookTracker.currentWidget.sessionContext;
        console.debug("RemoteSSH: labShell.restored, context.session.id =", context.session.id)

        this.update(context)
      }
    )
  }

  onConnectionStatusChange(context: ISessionContext, change: any) {
    console.log("onConnectionStatusChange", change)
    if (change == "disconnected") {
      this._extension.kernel_id = ""
      this._extension.kernel_name = ""
    } else if (change == "connected") {
      this.update(context)
    }
  }

  update(context: ISessionContext) {
    var id = context.session.kernel.id
    var name = context.kernelDisplayName
    console.log("RemoteSSH:", name, id)
    this._extension.kernel_id = id
    this._extension.kernel_name = name
  }
}

/**
 * Initialization data for the interrupt-ipykernel-extension extension.
 */

function activate(app: JupyterFrontEnd, notebookTracker: INotebookTracker, labShell: ILabShell): void {
  let buttonExtension = new InterruptButtonExtension();
  app.docRegistry.addWidgetExtension('Notebook', buttonExtension);
  new RemoteSSH(buttonExtension, notebookTracker, labShell)
}

const extension: JupyterFrontEndPlugin<void> = {
  id: 'interrupt-ipykernel-extension',
  requires: [INotebookTracker, ILabShell],
  autoStart: true,
  activate
};

export default extension;
