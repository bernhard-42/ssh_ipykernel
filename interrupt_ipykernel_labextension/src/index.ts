import {
  IDisposable
} from '@phosphor/disposable';

import {
  ToolbarButton
} from '@jupyterlab/apputils';

import {
  URLExt
} from '@jupyterlab/coreutils';

import {
  ServerConnection
} from '@jupyterlab/services';

import {
  DocumentRegistry
} from '@jupyterlab/docregistry';

import {
  NotebookPanel, INotebookModel
} from '@jupyterlab/notebook';

import {
  JupyterFrontEnd, JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { INotebookTracker } from '@jupyterlab/notebook';

class InterruptButtonExtension implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel> {
  private _notebookTracker: INotebookTracker;
  private host: string = "test-host";
  private pid: number = 1234;

  constructor(notebookTracker: INotebookTracker) {
    this._notebookTracker = notebookTracker;
  }

  createNew(panel: NotebookPanel, context: DocumentRegistry.IContext<INotebookModel>): IDisposable {

    let interrupt = () => {
      console.log('Interrupt clicked.');
      this._notebookTracker.currentWidget.session.kernel.interrupt()
      Private.interrupt({ host: this.host, pid: this.pid })
    };

    // Create the toolbar button 
    let button = new ToolbarButton({
      className: 'interrupt remote kernel',
      iconClassName: 'fa fa-stop-circle',
      onClick: interrupt,
      tooltip: 'Interrupt remote kernel'
    });

    // Add the toolbar button to the notebook
    panel.toolbar.insertItem(7, 'runAllCells', button);

    // The ToolbarButton class implements `IDisposable`, so the
    // button *is* the extension for the purposes of this method.
    return button;
  }
}

namespace Private {
  const SERVER_CONNECTION_SETTINGS = ServerConnection.makeSettings();

  export interface IDbStatusRequestResult {
    status: string;
  }

  async function request(command: string, host: string, pid: number) {
    var url = URLExt.join(SERVER_CONNECTION_SETTINGS.baseUrl, command);
    url = url + "?pid=" + pid + "&host=" + host;

    return ServerConnection.makeRequest(url, {}, SERVER_CONNECTION_SETTINGS);
  }

  export async function interrupt({ host, pid }: { host: string; pid: number; }) {
    const response = await request("interrupt", host, pid);
    if (response.ok) {
      var result = await response.json();
      console.log(result)
    } else {
      console.error("interrupt response: unknown", response)
    }
  }
}

/**
 * Initialization data for the interrupt-ipykernel-extension extension.
 */
function activate(app: JupyterFrontEnd, notebookTracker: INotebookTracker): void {
  let buttonExtension = new InterruptButtonExtension(notebookTracker);
  app.docRegistry.addWidgetExtension('Notebook', buttonExtension);
}

const extension: JupyterFrontEndPlugin<void> = {
  id: 'interrupt-ipykernel-extension',
  requires: [INotebookTracker],
  autoStart: true,
  activate
};

export default extension;
