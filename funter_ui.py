import pymel.core as pc
from . import funter_crowd
import os

reload(funter_crowd)
Funter = funter_crowd.Funter
FunterReplacer = funter_crowd.FunterReplacer


class FunterUI(object):
    def __init__(self, funter, replacer, uiparent):
        self.funter = funter
        self.replacer = replacer
        self.uiparent = uiparent
        self.setupUI()
        self._set_path()

    def setupUI(self):
        pc.setParent(self.uiparent)
        with pc.rowLayout(
                w=800, nc=5, cw5=[30, 135, 135, 400, 100]) as self.mainLayout:
            self.checkBox = pc.checkBox(v=False, l='')
            self.animText = pc.text(l=self.funter.anim)
            self.charText = pc.text(l=self.funter.char)
            self.pathField = pc.textFieldButtonGrp(
                    cw2=[350, 50], buttonLabel='...',
                    changeCommand=self.checkPath,
                    buttonCommand=self.browseForProxy)
            self.statusField = pc.text()

    def isSelected(self):
        return self.checkBox.getValue()

    def select(self):
        if self.checkBox.getEnable():
            self.checkBox.setValue(True)

    def unselect(self):
        if self.checkBox.getEnable():
            self.checkBox.setValue(False)

    def delete(self):
        pc.deleteUI(self.mainLayout)

    def getPath(self):
        return self.pathField.getFileName()

    def setStatus(self, status, red=False):
        self.statusField.setLabel(status)
        if red:
            self.statusField.setBackgroundColor((1, 0.5, 0.5))
        else:
            self.statusField.setEnableBackground(False)

    def browseForProxy(self):
        mydir = self.pathField.getFileName()
        result = pc.fileDialog2(fm=1, dir=mydir, ff='*.rs')
        if result:
            self.setPath(result[0])

    def setPath(self, path):
        self.pathField.setFileName(path)
        self.checkPath()


class FunterWithoutProxyUI(FunterUI):

    def _set_path(self):
        path = self.replacer.get_proxy_path(self.funter)
        if path:
            self.setPath(path)
            self.setStatus('Proxy Found')
        else:
            self.setStatus('Cannot Find Proxy', True)

    def checkPath(self, *args):
        path = self.pathField.getFileName()
        if os.path.isfile(path):
            self.setStatus('Proxy Found')
            self.checkBox.setEnable(True)
            return False
        else:
            self.setStatus('Proxy Not Found', True)
            self.checkBox.setValue(False)
            self.checkBox.setEnable(False)
            return True


class FunterWithProxyUI(FunterUI):

    def _set_path(self):
        proxy = self.replacer.get_proxy(self.funter)
        path = None
        if proxy:
            path = proxy.fileName.get()

        if path:
            if os.path.isfile(path):
                self.pathField.setFileName(path)
                self.setStatus('OK')
            else:
                self.setStatus('Proxy path does not exist', True)
        else:
            self.setStatus('Proxy not connected', True)

    def setPath(self, path):
        if self.checkPath():
            proxy = self.replacer.get_proxy(self.funter)
            expr_made = self.replacer.set_proxy_path(
                    proxy, path, self.funter.get_anim_offset())
            if not expr_made:
                self.setStatus('Proxy is not a sequence')
            else:
                self.setStatus('OK')
            self.pathField.setFileName(path)
        else:
            pc.error('Specified File does not exist')

    def setupUI(self):
        super(FunterWithProxyUI, self).setupUI()
        self.pathField.setEditable(False)

    def checkPath(self, *args):
        path = self.pathField.getFileName()
        if os.path.isfile(path):
            return False
        else:
            return True


class FunterReplacerUI(object):
    __winname__ = 'FunterReplacerUI'
    __proxy_base__ = r'\\library\storage\Proxies\EBM\CrowdSetups\Ad02\Loop'

    def __init__(self):
        self.setupui()
        self.funters_with = []
        self.funters_wo = []

    def setupui(self):
        if pc.window(self.__winname__, exists=True):
            self.delete()

        with pc.window(self.__winname__, width=850, height=800) as self.win:
            with pc.columnLayout(adj=True):
                self.basepath_textgrp = pc.textFieldButtonGrp(
                        label='Base Dir For Proxies: ',
                        fi=self.__proxy_base__,
                        buttonLabel='...',
                        cw3=[125, 600, 100],
                        ct3=['Both', 'Both', 'Both'],
                        buttonCommand=self.browseForBaseProxyFolder)
                pc.button(l='Populate Funters', c=self.populateFunters)

                with pc.frameLayout(cll=True, l='Funters Without Proxy'):
                    with pc.columnLayout(adj=True, w=850):
                        with pc.scrollLayout(h=400, w=850):
                            with pc.columnLayout(adj=True) as self.woutlayout:
                                pass
                        with pc.rowLayout(
                                adj=True, nc=3, cw3=[50, 100, 100]):
                            self.checkBoxWO = pc.checkBox(
                                    l='', cc=self.toggleWO)
                            pc.button(
                                    l='Select Rig', w=100,
                                    c=self.selectRigs)
                            pc.button(
                                    l='Bring Proxy', w=100,
                                    c=self.bringProxies)

                with pc.frameLayout(
                        cll=True, l='Funters With Proxy', collapse=True):
                    with pc.columnLayout(adj=True, w=850):
                        with pc.scrollLayout(h=200, w=850):
                            with pc.columnLayout(adj=True) as self.withlayout:
                                    pass
                        with pc.rowLayout(
                                adj=True, nc=3, cw3=[50, 100, 100]):
                            self.checkBoxWith = pc.checkBox(
                                    l='', cc=self.toggleWith)
                            pc.button(
                                    l='Select Proxy', w=100,
                                    c=self.selectProxies)
                            pc.button(
                                    l='Delete Proxy', w=100,
                                    c=self.deleteProxies)

                pc.button('close', c=self.delete)

    def bringProxies(self, *args):
        for funterui in self.funters_wo:
            if funterui.isSelected():
                self.replacer.replace_with_proxy(
                        funterui.funter, path=funterui.getPath())
        self.updateFunters()

    def deleteProxies(self, *args):
        for funterui in self.funters_with:
            if funterui.isSelected():
                pc.delete(self.replacer.get_proxy_node_name(funterui.funter))
        self.updateFunters()

    def selectRigs(self, *args):
        pc.select(cl=True)
        for funterui in self.funters_wo:
            if funterui.isSelected():
                pc.select(funterui.funter.root, add=True)

    def selectProxies(self, *args):
        pc.select(cl=True)
        for funterui in self.funters_with:
            if funterui.isSelected():
                name = self.replacer.get_proxy_node_name(funterui.funter)
                pc.select(name, add=True)

    def toggleWO(self, *args):
        if self.checkBoxWO.getValue():
            self.markAllWO()
        else:
            self.unmarkAllWO()

    def toggleWith(self, *args):
        if self.checkBoxWith.getValue():
            self.markAllWith()
        else:
            self.unmarkAllWith()

    def markAllWO(self):
        for funterui in self.funters_wo:
            funterui.select()

    def markAllWith(self):
        for funterui in self.funters_with:
            funterui.select()

    def unmarkAllWO(self):
        for funterui in self.funters_wo:
            funterui.unselect()

    def unmarkAllWith(self):
        for funterui in self.funters_with:
            funterui.unselect()

    def populateFunters(self, *args):
        self.replacer = FunterReplacer(self.proxy_base_path)
        self.funters = Funter.getFuntersFromRefs()
        self.updateFunters()

    def clearFunters(self):
        for child in self.funters_with:
            child.delete()
        self.funters_with = []
        for child in self.funters_wo:
            child.delete()
        self.funters_wo = []

    def updateFunters(self):
        self.clearFunters()
        for funter in self.funters:
            if not self.replacer.proxy_exists(funter):
                elem = FunterWithoutProxyUI(
                        funter, self.replacer, self.woutlayout)
                self.funters_wo.append(elem)
            else:
                elem = FunterWithProxyUI(
                        funter, self.replacer, self.withlayout)
                self.funters_with.append(elem)

    def browseForBaseProxyFolder(self, *args):
        mydir = self.basepath_textgrp.getFileName()
        result = pc.fileDialog2(fm=2, dir=mydir)
        if result:
            self.basepath_textgrp.setFileName(result[0])

    def show(self):
        pc.showWindow(self.win)

    def delete(self, *args):
        pc.deleteUI(self.__winname__, window=True)

    @property
    def proxy_base_path(self):
        return self.basepath_textgrp.getFileName()


def main():
    FunterReplacerUI().show()


if __name__ == "__main__":
    main()
