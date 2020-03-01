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

import {
  INotebookTracker
} from '@jupyterlab/notebook';

import {
  Kernel
} from '@jupyterlab/services';

declare global {
  interface Window { ssh_ipykernel: any; }
}

class InterruptButtonExtension implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel> {
  private _notebookTracker: INotebookTracker;
  private host: string = "";
  private pid: number = -1;

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

    return button;
  }

  get_pid(kernel: Kernel.IKernelConnection) {
    class ReplyData { "text/plain": string; }
    class ReplyContent { data: ReplyData }

    var future = kernel.requestExecute({
      code: "import os",
      user_expressions: { pid: "os.getpid()", host: "os.environ['SSH_IPYKERNEL_HOST']" }
    });

    future.done.then((reply) => {
      if (reply.content.status == "ok") {
        var ue = reply.content.user_expressions

        let pid_obj = new ReplyContent()
        Object.assign(pid_obj, ue["pid"])
        this.pid = Number(pid_obj.data["text/plain"])

        var host_obj = new ReplyContent()
        Object.assign(host_obj, ue["host"])
        var host = host_obj.data["text/plain"]
        this.host = host.substring(1, host.length - 1)
        console.info("host=", this.host, "pid=", this.pid)
      }
    })
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

  notebookTracker.currentChanged.connect((slot: any, notebookPanel: NotebookPanel) => {
    if (!notebookTracker.currentWidget) {
      return;
    }
    const notebookContext = notebookTracker.currentWidget.context;
    notebookContext.ready.then(() => {
      return notebookTracker.currentWidget.session.ready;
    }).then(() => {
      return notebookTracker.currentWidget.revealed;
    }).then(() => {
      return notebookPanel.session.kernel.ready;
    }).then(() => {
      var kernel = notebookPanel.session.kernel
      console.debug("Current kernel =", kernel)
      window.ssh_ipykernel = kernel;
      buttonExtension.get_pid(kernel);
    })
  })
}

const extension: JupyterFrontEndPlugin<void> = {
  id: 'interrupt-ipykernel-extension',
  requires: [INotebookTracker],
  autoStart: true,
  activate
};

export default extension;
