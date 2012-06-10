#!/usr/bin/env python
# -*- coding: utf-8 -*-

from inspect  import getdoc, isbuiltin
from .helpers import getargspec, getoptmetas, autotype, smartlyadd 

class ScanError(Exception): pass

class Command(object):
    '''Make a function, a built-in function or a bound method accepts
    arguments from command line.

    .. versionchanged:: 0.1.4
       It is almost rewritten.'''

    metatypes = {'N': int, 'NUM': int}

    @staticmethod
    def defautotype(x):
        '''The default type auto-detection function. It use `autotype` by
        default.'''
        return autotype(x)

    def __init__(self, func):
        args, vararg, keyword, defvals = getargspec(func)

        # basic infomation
        self.func = func
        self.args = args
        self.vararg = vararg
        #self.keyword = keyword

        # `args` are the arguments from original function
        # arg indexed
        self.defaults = {}
        self.modeflags = set()
        self.refers = {} # options wich bind this arg

        # `opts` are the optional arguments
        # opt indexed
        self.metavars = {}
        self.bindings = {} # it map to arg

        # collect options and default value

        optset = set()
        self.hasdefidx = len(args) - len(defvals)
        for i, arg in enumerate(args):
            if i >= self.hasdefidx:
                # optional argument (has default)
                opt = '-' * (1+(len(args)>1)) + arg.replace('_', '-')
                optset.add(opt)
                self.bindings[opt] = arg
                self.refers[arg] = [opt]
                defval = defvals[i-self.hasdefidx]
                self.defaults[arg] = defval
                if isinstance(defval, bool):
                    self.modeflags.add(arg)

        doc = getdoc(func)
        if not doc: return

        # collect more options (aliases) and metavars from doc

        for lineoptmetas in getoptmetas(doc):
            targetoptset = optset & set(om[0] for om in lineoptmetas)
            if len(targetoptset) > 0:
                targetopt = targetoptset.pop()
                targetarg = targetopt.lstrip('-').replace('-', '_')
            else:
                continue
            for opt, meta in lineoptmetas:
                if meta is not None:
                    self.metavars[opt] = meta
                self.bindings[opt] = targetarg
                if opt != targetopt:
                    self.refers[targetarg].append(opt)

    def getoptspec(self, opt):
        '''return a 3-tuple (argname, defaultvalue, type)'''

        def mktypewrapper(type_):
            def typewrapper(obj):
                try:
                    return type_(obj)
                except ValueError:
                    raise ScanError("option '%s' must be %s" % (opt, type_.__name__))
            return typewrapper

        arg = self.bindings.get(opt, opt.lstrip('-'))
        metavar = self.metavars.get(opt, opt.upper())
        _type = self.metatypes.get(metavar, self.defautotype)
        twrapper = mktypewrapper(_type)

        return (arg, twrapper)

    def getdefault(self, opt):
        arg = self.bindings.get(opt, arg)
        default = self.defaults.get(arg, object)

        return default

    def scan(self, rawargs=None):
        '''Scan the `rawargs`, and return a tuple (`pargs`, `kargs`).

        `rawargs` can be `string` or `list`.

        Uses *keyword-first resolving* -- If keyword and positional arguments
        are at same place, the keyword argument will take this place and push
        the positional argument to next.

        Example:

        >>> def files(mode='r', *paths):
        >>>     print mode, paths
        >>> 
        >>> files_cmd = Command(files)
        >>> files_cmd.scan('--mode w f1.txt f2.txt')
        (['w', 'f1.txt', 'f2.txt'], {})
        >>> files_cmd('--mode w f1.txt f2.txt')
        w ('f1.txt', 'f2.txt')    

        If an no-value options is found and the value in default of function is
        boolean, it will put the opposite boolean into `optargs`.

        >>> def test(b=True, x=None):
        >>>     print b, x
        >>> 
        >>> test_cmd = Command(test)
        >>> test_cmd('-b')
        False None

        If duplicate options are found and

        1. the default of function is boolean: it will count this options;
        2. otherwise: it will put the value into a list.

        >>> test_cmd('-bbb -x first -x second -x third')
        3 ['first', 'second', 'third']

        .. versionchanged:: 0.1.4
           Use custom parser instead of `getopt`.

        .. versionchanged:: 0.1.4
           It is rewritten from `Command.parse` (0.1.3).

        '''

        def nextarg():
            if rawargs and not rawargs[0].startswith('-'):
                return rawargs.pop(0)
            else:
                raise ScanError("option '%s' needs a value" % opt)

        # collect the aliases and metavars
        self.bindings = {}
        self.metavars = {}
        doc = getdoc(func)
        if not doc: return 

        args = set(args)
        for optmetas in getoptmetas(doc):
            for opt, meta in optmetas:
                self.metavars[opt] = meta
            opts, metas = zip(*optmetas)
            opts = set(opts)
            try:
                target = (opts & args).pop()
            except KeyError: # can't find target
                pass
            else:
                opts -= args
                for opt in opts:
                    self.bindings[opt] = target

    def scan(self, rawargs):
        '''Scan the `rawargs`, and return a tuple (`pargs`, `kargs`).

        `rawargs` can be `string` or `list`.

        Uses *keyword-first resolving* -- If keyword and positional arguments
        are at same place, the keyword argument will take this place and push
        the positional argument to next.

        Example:

        >>> def files(mode='r', *paths):
        >>>     print mode, paths
        >>> 
        >>> files_cmd = Command(files)
        >>> files_cmd.scan('--mode w f1.txt f2.txt')
        (['w', 'f1.txt', 'f2.txt'], {})
        >>> files_cmd('--mode w f1.txt f2.txt')
        w ('f1.txt', 'f2.txt')    

        If an no-value options is found and the value in default of function is
        boolean, it will put the opposite boolean into `optargs`.

        >>> def test(b=True, x=None):
        >>>     print b, x
        >>> 
        >>> test_cmd = Command(test)
        >>> test_cmd('-b')
        False None

        If duplicate options are found and

        1. the default of function is boolean: it will count this options;
        2. otherwise: it will put the value into a list.

        >>> test_cmd('-bbb -x first -x second -x third')
        3 ['first', 'second', 'third']

        .. versionchanged:: 0.1.4
           Use custom parser instead of `getopt`.

        .. versionchanged:: 0.1.4
           It is rewritten from `Command.parse` (0.1.3).

        '''

        def mktypewrapper(t):
            def typewrpper(o):
                try:
                    return t(o)
                except ValueError:
                    raise ScanError("option '%s' must be %s" % (opt, t.__name__))
            return typewrpper

        def gettype(opt):
            meta = self.metavars.get(opt, None)
            t = self.metatypes.get(meta, self.defautotype)
            return mktypewrapper(t)

        def nextarg():
            if rawargs and not rawargs[0].startswith('-'):
                return rawargs.pop(0)
            else:
                raise ScanError("option '%s' needs a value" % opt)

        if isinstance(rawargs, str):
            rawargs = rawargs.split()
        else:
            rawargs = rawargs[:]

        pargs = []
        kargs = {}

        while rawargs:
            piece, _, npiece = rawargs.pop(0).partition('=')
            if npiece: rawargs.insert(0, npiece)

            plen = len(piece)
            if piece.startswith('-'):

                if plen >= 3 and piece[1] == '-':
                    # keyword option: --options [value]
                    opt = piece
                    key, type_  = self.getoptspec(opt)
                    vals = kargs.setdefault(key, [])
                    if key in self.modeflags:
                        vals.append( None )
                    else:
                        vals.append( type_( nextarg() ) )
                    continue

                if plen >= 2:
                    # letter option: -abco[value] or --abco [value]
                    epiece = enumerate(piece); next(epiece)
                    for i, opt in epiece:
                        opt = '-' + opt
                        key, type_  = self.getoptspec(opt)
                        vals = kargs.setdefault(key, [])
                        if key in self.modeflags:
                            vals.append( None )
                        else:
                            if i == plen-1:
                                # -abco value
                                val = nextarg()
                            else:
                                # -abcovalue
                                val = piece[i+1:]
                            vals.append( type_(val) )
                            break
                    continue

            # if doesnt start with '-' or length of piece is not enough
            pargs.append( self.defautotype(piece) )

        # reduce the collected values
        for key, vals in kargs.iteritems():
            val = reduce(smartlyadd, vals, object)
            kargs[key] = val

        # toggle the bool default value
        for modeflag in self.modeflags:
            if kargs.get(modeflag, 0) is None:
                kargs[modeflag] = not self.defaults[modeflag]

        # copy the default value
        kposes = dict( (k,i) for i, k in enumerate(self.args))
        plen = len(pargs)
        for key, value in self.defaults.iteritems():
            if key not in kargs and plen < kposes[key]:
                kargs[key] = value

        # de-keyword (keyword-first resolving)
        for pos, argname in enumerate(self.args):
            plen = len(pargs)
            if pos > plen: break
            try:
                val = kargs[argname]
            except KeyError:
                pass
            else:
                pargs.insert(pos, val)
                del kargs[argname]

        # map all of the optargs to posargs for `built-in function`,
        # because a `built-in function` only accept positional arguments
        if isbuiltin(self.func):
            for key, value in kargs.items():
                try:
                    pargs[self.args.index(key)] = value
                except ValueError:
                    pass
                else:
                    kargs = {}
            try:
                pargs = pargs[:-pargs.index(None) or None]
            except ValueError:
                pass

        return pargs, kargs

    def execute(self, rawargs):
        '''Execute this command with `rawargs`.'''

        pargs, kargs = self.scan(rawargs)
        return self.func(*pargs, **kargs)

    def getusage(self, isdefault=False):
        '''Return the usage of this command.

        Example: ::

            files [--mode VAL] [PATHS]...

        If `isdefault` is True, it will render usage without function name.
        '''

        optargs = self.defaults.keys()
        optargs.sort()

        rbindings = {}
        for opt, target in self.bindings.iteritems():
            shortcuts = rbindings.setdefault(target, [])
            shortcuts.append(opt)

        usage = []

        for optarg in optargs:
            opts = [optarg]
            opts.extend( rbindings.get(optarg, []) )
            for i, opt in enumerate(opts):
                opts[i] ='%s%s' % ('-' * (1+(len(opt)>1)), opt.replace('_', '-'))
                meta = self.metavars.get(opt, None)
                if meta:
                    opts[i] += ' '+meta
            usage.append('[%s]' % ' | '.join(opts))

        posargs = self.args[:-len(optargs) or None]
        usage.extend( map(str.upper, posargs) )

        if self.vararg:
            usage.append('[%s]... ' % self.vararg.upper())

        if isdefault:
            return '%s' % ' '.join(usage)
        else:
            name = self.func.__name__
            return '%s %s' % (name, ' '.join(usage))
