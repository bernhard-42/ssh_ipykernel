import {
  IDisposable
} from '@phosphor/disposable';

import {
  ToolbarButton
} from '@jupyterlab/apputils';

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

  constructor(notebookTracker: INotebookTracker) {
    this._notebookTracker = notebookTracker;
  }

  createNew(panel: NotebookPanel, context: DocumentRegistry.IContext<INotebookModel>): IDisposable {
    // Create the on-click callback for the toolbar button.
    let runAllCells = () => {
      console.log('Interrupt clicked.');
      this._notebookTracker.currentWidget.session.kernel.interrupt()
    };

    // Create the toolbar button 
    let button = new ToolbarButton({
      className: 'interrupt remote kernel',
      iconClassName: 'fa fa-stop-circle',
      onClick: runAllCells,
      tooltip: 'Run All Cells'
    });

    // Add the toolbar button to the notebook
    panel.toolbar.insertItem(7, 'runAllCells', button);

    // The ToolbarButton class implements `IDisposable`, so the
    // button *is* the extension for the purposes of this method.
    return button;
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
