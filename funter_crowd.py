import pymel.core as pc
from pymel.core.language import Mel
import os
import logging
import re
import sys

from . import utilities


reload(utilities)
get_pattern = utilities.get_pattern
get_first_keyframe = utilities.get_first_keyframe


__all__ = ['Funter', 'FunterReplacer']


class Funter(object):

    def __init__(self, refnode=None, anim=None, char=None, root=None):
        self.refnode = refnode
        self._anim = anim
        self._char = char
        self._root = root
        if not anim:
            self._assign_anim()
        if not char:
            self._assign_char()
        if not root:
            self._assign_nodes()

    @property
    def char(self):
        if self._char is None:
            self._assign_char()
        return self._char

    @property
    def anim(self):
        if self._anim is None:
            self._assign_anim()
        return self._anim

    @property
    def root(self):
        if self._root is None:
            self._assign_nodes()
        return self._root

    def __str__(self):
        return '<Funter %s, %s, %s>' % (self.char, self.anim, self.root)

    def _assign_char(self):
        self._char = '_'.join(os.path.basename(self._reffile.path).split(
            '_')[:-1])

    def _assign_anim(self):
        if self.root.fullPath().split('|')[1] == 'Crowd_grp':
            self._anim = self.root.fullPath().split('|')[2]
        else:
            raise ValueError('Funter Not part of Crowd Grp')

    def _assign_nodes(self):
        root = self._reffile.nodes()[0]
        for node in root.getChildren()[0].getChildren():
            if node.name().endswith('Main'):
                self._root = node
                return
        raise ValueError('Main node not found')

    @property
    def reffile(self):
        self._reffile

    @property
    def refnode(self):
        return self._refnode

    @property
    def namespace(self):
        return self.refnode.associatedNamespace(False)

    @refnode.setter
    def refnode(self, refnode):
        if refnode is None:
            self._refnode = None
            self._reffile = None
            return
        self._refnode = refnode
        reffile = self._refnode.referenceFile()
        if reffile is None:
            raise ValueError('Only File Reference Nodes are accepted')
        self._refnode = refnode
        self._reffile = reffile

    @classmethod
    def getFuntersFromRefs(cls):
        funters = []
        progressBar = Mel.globals['$gMainProgressBar']
        refnodes = pc.ls(type='reference')
        pc.progressBar(
                progressBar, edit=True, beginProgress=True,
                isInterruptable=True, status='Loading Funters ...',
                maxValue=len(refnodes))
        for refnode in refnodes:
            if pc.progressBar(progressBar, q=True, isCancelled=True):
                break
            try:
                funters.append(Funter(refnode))
            except Exception as exc:
                logging.debug(exc)
            pc.progressBar(progressBar, edit=True, step=1)
        pc.progressBar(progressBar, edit=True, endProgress=True)
        return funters

    def get_anim_offset(self):
        return get_first_keyframe(self.root, ignore_top_node=True)

    def remove(self):
        pass


class FunterReplacer(object):
    rsexpr = r'(.*?)[\._](\d+)\.rs'
    expression = '%s.frameExtension = %d + (frame + %d) %% %d'
    proxyPrefix = 'FunterProxy_'

    def __init__(self, proxies_path, proxy_parent='FunterProxies'):
        self.base_proxy_path = proxies_path
        self.proxy_parent = proxy_parent

    def get_proxy_path(self, funter):
        dirname = os.path.join(self.base_proxy_path, funter.anim, funter.char)
        name = None
        _min = sys.maxint

        if os.path.isdir(dirname):
            for filename in os.listdir(dirname):
                match = re.match(self.rsexpr, filename)
                if match:
                    num = int(match.group(2))
                    if num < _min:
                        _min = num
                        name = filename

        if name is not None:
            return os.path.join(dirname, name)

    def set_proxy_path(self, proxy, path, offset):
        proxy.useFrameExtension.set(0)
        pc.delete(proxy.frameExtension.inputs())
        pattern, _min, _max = get_pattern(path)
        proxy.fileName.set(path)
        if pattern is not None:
            pc.expression(s=self.expression % (
                proxy.name(), _min, offset, _max+1))
            proxy.useFrameExtension.set(1)
            return False
        return True

    def create_proxy(self):
        meshShape = pc.createNode('mesh')
        proxy = pc.createNode('RedshiftProxyMesh')
        proxy.outMesh.connect(meshShape.inMesh)
        return meshShape

    def get_proxy_node_name(self, funter):
        return '|' + '|'.join([
            self.proxy_parent, funter.anim, self.proxyPrefix +
            funter.namespace])

    def proxy_exists(self, funter):
        return pc.objExists(self.get_proxy_node_name(funter))

    def replace_with_proxy(self, funter, path=None):
        if path is None:
            path = self.get_proxy_path(funter)
        meshShape = self.create_proxy()
        offset = funter.get_anim_offset()
        self.set_proxy_path(meshShape.inMesh.inputs()[0], path, offset)
        mesh = meshShape.firstParent()
        pc.parent(mesh, self.ensure_parent(funter))
        mesh.rename(self.proxyPrefix + funter.namespace)
        pc.xform(
            mesh, ws=True,
            matrix=pc.xform(funter.root, q=True, ws=True, matrix=True))
        for at in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
            keyframes = pc.keyframe(funter.root.attr(at), q=True)
            keys = pc.copyKey(funter.root, t=':', at=at)
            if keys:
                pc.pasteKey(mesh, time=keyframes[0], connect=True, at=at)
        pc.sets('initialShadingGroup', fe=mesh)
        return mesh

    def get_proxy(self, funter):
        try:
            mesh = pc.PyNode(self.get_proxy_node_name(funter))
            return mesh.getShape().inMesh.inputs()[0]
        except Exception as exc:
            print exc

    def ensure_parent(self, funter):
        if not pc.objExists(self.proxy_parent):
            pc.createNode('transform', n=self.proxy_parent)
        parent = '|' + '|'.join([self.proxy_parent, funter.anim])
        if not pc.objExists(parent):
            pc.createNode('transform', n=funter.anim, p=self.proxy_parent)
        return pc.PyNode(parent)

    def replace_with_proxies(self):
        proxies = []
        allfunters = Funter.getFuntersFromRefs()
        for funter in allfunters:

            if self.proxy_exists(funter):
                pc.warning('proxy for funter %s already exists' % funter)
                continue

            path = None
            try:
                path, _ = self.get_proxy_path(funter)
            except Exception:
                pass

            if path is None:
                pc.warning('proxy not found for funter %s' % funter)
                continue

            proxy = self.replace_with_proxy(funter)
            if proxy:
                proxies.append(proxy)
                funter.remove()
        return proxies


if __name__ == "__main__":
    path = r'\\library\storage\Proxies\EBM\CrowdSetups\Ad02\test'
    for x in Funter.getFuntersFromRefs():
        print x
    replacer = FunterReplacer(path)
    replacer.replace_with_proxies()
