#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 27 11:52:46 2022

@author: drupke
"""

import numpy as np
import os.path

from q3dfit.readcube import Cube


class q3din:
    '''
    Initialize fit.

    Parameters
    -----------
    infile : str
         Name of input FITS file.
    argsreadcube : dict
    cutrange :
    fitrange : list
        2-element array specifying range over which to fit
    label : str
        Shorthand label for filenames
    logfile : str
    name : str
        Full name of source for plot labels, etc.
    outdir : str
        Output directory for files
    spect_convol : dict
    vacuum : bool
    zsys_gas : float

    Attributes
    ----------
    docontfit : bool
    dolinefit : bool
        Are emission lines or continuum fit? Not unless init_linefit and/or
        init_contfit is run.

    Examples
    --------
    >>> from q3dfit import q3di
    >>> q3di = q3din('file.fits')

    Notes
    -----
    '''

    def __init__(self, infile, label, argsreadcube={}, cutrange=None,
                 docontfit=False, fitrange=None,
                 logfile=None, name=None, outdir=None,
                 spect_convol={}, zsys_gas=None,
                 datext=1, varext=2, dqext=3, vormap=None,
                 vacuum=True):

        self.argsreadcube = argsreadcube
        self.cutrange = cutrange
        self.infile = infile
        self.fitrange = fitrange
        self.label = label
        self.logfile = logfile
        self.name = name
        self.outdir = outdir
        self.spect_convol = spect_convol
        self.vacuum = vacuum
        self.zsys_gas = zsys_gas

        self.datext = datext
        self.varext = varext
        self.dqext = dqext
        self.vormap = vormap

        self.docontfit = False
        self.dolinefit = False

    def init_linefit(self, lines, linetie=None, maxncomp=1, siginit=50.,
                     zinit=None,
                     argscheckcomp={}, argslineinit={}, argslinefit={},
                     argslinelist={}, checkcomp=True,
                     fcnlineinit='lineinit',
                     fcncheckcomp='checkcomp', noemlinfit=True,
                     peakinit=None,
                     siglim_gas=None):
        '''
        Initialize line fit.

        Parameters
        ----------
        argscheckcomp : dict
        argslineinit : dict
        argslinefit : dict
        argslinelist : dict
        checkcomp : bool
            Filter # of components.
        fcncheckcomp : str
            Name of routine for filtering # of components.
        fcnlineinit : str
        linetie : list
            If not set, all lines are fit independently. If it's a single
            line, all lines are tied together. Otherwise,
            each linetie corresponds to an element in lines.
        maxncomp : int
            Maximum possible # of velocity components in any line.
        peakinit : dict
            Initial guess for peak flux for each line and component.
        siginit : float
        zinit : float
            Initial redshift, sigma in km/s to apply to each line. If zinit
            is not specified and zsys_gas is defined, use that.

        Attributes
        ----------
        linetie : dict
        ncomp : dict
        siginit_gas : dict
        zinit_gas : dict

        '''
        # check for defined zsys
        if zinit is None:
            if self.zsys_gas is not None:
                zinit = self.zsys_gas
            else:
                print('problem!')

        self.lines = lines

        self.argscheckcomp = argscheckcomp
        self.argslineinit = argslineinit
        self.argslinefit = argslinefit
        self.argslinelist = argslinelist
        self.checkcomp = checkcomp
        self.fcncheckcomp = fcncheckcomp
        self.fcnlineinit = fcnlineinit
        self.maxncomp = maxncomp
        self.peakinit = peakinit
        self.siglim_gas = siglim_gas

        # flip this switch
        self.dolinefit = True

        # set up linetie dictionary
        # case of no lines tied
        if linetie is None:
            linetie = lines
        # case of all lines tied -- single string
        elif isinstance(linetie, str):
            linetie = [linetie] * len(lines)
        elif len(linetie) != len(lines):
            print('q3di: If you are tying lines together in different groups' +
                  ', linetie must be the same length as lines')

        # check that load_cube() has been invoked, or ncols/nrows otherwise
        # defined
        if not hasattr(self, 'ncols') or not hasattr(self, 'nrows'):
            _ = self.load_cube(self.infile)
            print('q3di: Loading cube to get ncols, nrows')

        # set up dictionaries to hold initial conditions
        self.linetie = {}
        self.ncomp = {}
        self.siginit_gas = {}
        self.zinit_gas = {}
        for i, line in enumerate(self.lines):
            self.linetie[line] = linetie[i]
            self.ncomp[line] = np.full((self.ncols, self.nrows),
                                       self.maxncomp)
            self.zinit_gas[line] = np.full((self.ncols, self.nrows,
                                            self.maxncomp), zinit)
            self.siginit_gas[line] = np.full((self.ncols, self.nrows,
                                              self.maxncomp), siginit)

    def init_contfit(self, fcncontfit, siginit=50., zinit=None, argscontfit={},
                     argscontplot={}, argsconvtemp={},
                     decompose_qso_fit=False, decompose_ppxf_fit=False,
                     dividecont=False, ebv_star=None,
                     fcncontplot='plotcont', fcnconvtemp=None,
                     keepstarz=False,
                     masksig_secondfit=2., maskwidths=None, maskwidths_def=500.,
                     nolinemask=False, nomaskran=None,
                     startempfile=None, startempvac=True, tweakcntfit=None):
        '''
        Initialize continuum fit.

        Parameters
        ----------
        fcncontfit : str
            Function to fit continuum. Assumed to be a method in
            contfit module of q3dfit package.
            Exception is ppxf, can just specify 'ppxf'.
        fcnconvtemp : str
            Function with which to convolve template before fitting.
            (Not yet implemented.)

        argscontfit : dict
        argsconvtemp : dict

        decompose_qso_fit : bool
        decompose_ppxf_fit : bool
        dividecont : bool
            Divide data by continuum fit. Default is to subtract.
        ebv_star : float
        keepstarz : bool
            Don't redshift stellar template before fitting.
        masksig_secondfit : float
            When computing masking half-widths before second fit, sigmas from
            first fit are multiplied by this number.
        maskwidths : dict
            Can specify maskwidths on a per-line, per-component basis if
            desired, in km/s
        maskwidths_def : float, optional, default=500.
            Widths, in km/s, of regions to mask from continuum fit during
            first line fit.
        nolinemask : bool
            Don't mask emission lines before continuum fit.
        nomaskran: ndarray, optional
            type: np.array[2,nreg] offloating point values
            Set of lower and upper wavelength limits of regions not to mask.
        siginit : float
        startempvac : bool
            Is the stellar template in vacuum wavelengths?
        tweakcntfit : ndarray
        zinit : float
            Initial redshift, sigma in km/s to apply to each line. If zinit
            is not specified and zsys_gas is defined, use that.

        Attributes
        ----------
        siginit_stars : ndarray(ncols, nrows)
        zinit_stars : ndarray(ncols, nrows)
        '''

        self.fcncontfit = fcncontfit

        self.argscontfit = argscontfit
        self.argsconvtemp = argsconvtemp

        self.decompose_qso_fit = decompose_qso_fit
        self.decompose_ppxf_fit = decompose_ppxf_fit
        self.dividecont = dividecont
        self.ebv_star = ebv_star
        self.fcnconvtemp = fcnconvtemp
        self.keepstarz = keepstarz
        self.maskwidths = maskwidths
        self.maskwidths_def = maskwidths_def
        self.masksig_secondfit = masksig_secondfit
        self.nolinemask = nolinemask
        self.nomaskran = nomaskran
        self.startempfile = startempfile
        self.startempvac = startempvac
        self.tweakcntfit = tweakcntfit

        # flip this switch
        self.docontfit = True

        # check for defined zsys
        if zinit is None:
            if self.zsys_gas is not None:
                zinit = self.zsys_gas
            else:
                print('problem!')

        # check that load_cube() has been invoked, or ncols/nrows otherwise
        # defined
        if not hasattr(self, 'ncols') or not hasattr(self, 'nrows'):
            _ = self.load_cube(self.infile)
            print('q3di: Loading cube to get ncols, nrows')

        self.siginit_stars = np.full((self.ncols, self.nrows), siginit)
        self.zinit_stars = np.full((self.ncols, self.nrows), zinit)

    def load_cube(self):
        if not os.path.isfile(self.infile):
            print('Data cube not found.')
        else:
            cube = Cube(self.infile, datext=self.datext, varext=self.varext,
                        dqext=self.dqext, **self.argsreadcube)
            self.ncols = cube.ncols
            self.nrows = cube.nrows
            self.cubedim = cube.cubedim
            cube.about()
            return(cube)

#if __name__ == "__main__":
#    q3di = q3di()
