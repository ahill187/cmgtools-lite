import optparse, subprocess, ROOT, datetime, math, array, copy, os
import numpy as np

#doPUreweighting = True
doPUandSF = True

def submitFRrecursive(ODIR, name, cmd, dryRun=False):
    outdir=ODIR+"/jobs/"
    if not os.path.isdir(outdir): 
        os.system('mkdir -p '+outdir)
    os.system('cp ${{HOME}}/index.php {od}/../'.format(od=outdir))
    os.system('cp ${{HOME}}/resubFRs.py {od}/../../'.format(od=outdir))
    srcfile = outdir+name+".sh"
    logfile = outdir+name+".log"
    srcfile_op = open(srcfile,"w")
    srcfile_op.write("#! /bin/sh\n")
    srcfile_op.write("ulimit -c 0\n")
    srcfile_op.write("cd {cmssw};\neval $(scramv1 runtime -sh);\ncd {d};\n".format( 
            d = os.getcwd(), cmssw = os.environ['CMSSW_BASE']))
    srcfile_op.write(cmd+'\n')
    os.system("chmod a+x "+srcfile)
    bsubcmd = "bsub -q 1nd -o {logfile} {srcfile}\n".format(d=os.getcwd(), logfile=logfile, srcfile=srcfile)
    if dryRun: 
        print "[DRY-RUN]: ", bsubcmd
    else: os.system(bsubcmd)

def submitIt(ODIR, name, cmd, dryRun=True): #GO,name,plots=[],noplots=[],opts=None):
    outdir=ODIR+"/jobs/"
    if not os.path.isdir(outdir): 
        os.system('mkdir -p '+outdir)
    srcfile = outdir+name+".sh"
    logfile = outdir+name+".log"
    srcfile_op = open(srcfile,"w")
    srcfile_op.write("#! /bin/sh\n")
    srcfile_op.write("ulimit -c 0\n")
    srcfile_op.write("cd {cmssw};\neval $(scramv1 runtime -sh);\ncd {d};\n".format( 
            d = os.getcwd(), cmssw = os.environ['CMSSW_BASE']))
    srcfile_op.write(cmd+'\n')
    os.system("chmod a+x "+srcfile)
    bsubcmd = "bsub -q 8nh -o {logfile} {srcfile}\n".format(d=os.getcwd(), logfile=logfile, srcfile=srcfile)
    if dryRun: 
        print "[DRY-RUN]: ", bsubcmd
    else: os.system(bsubcmd)

def printAggressive(s):
    print '='.join('' for i in range(len(s)+1))
    print s
    print '='.join('' for i in range(len(s)+1))

def readScaleFactor(path, process, reterr = False):
    infile = open(path,'r')
    lines = infile.readlines()
    
    for line in lines:
        if 'Process {proc} scaled by'.format(proc=process) in line:
            scale = float(line.split()[4])
            scaleerr = float(line.split()[-1])
    if not reterr:
        return scale
    else:
        return scale, scaleerr

def readFakerate(path, process):
    infile = open(path,'r')
    lines = infile.readlines()
    index = 999
    for ind,line in enumerate(lines):
        if process in line and '===' in line:
            index = ind
    frs = []; errs = []
    for il, line in enumerate(lines):
        if il < index+3: continue
        if len(line)==1: break
        frs.append(float(line.split()[2]))
        down = float(line.split()[3].replace('--','-'))
        up   = float(line.split()[4].replace('++','+'))
        errs.append( (abs(down)+abs(up))/2.)
    ##fr  = float(lines[index+3].split()[2])
    ##err = (abs(float(lines[index+3].split()[3])) + abs(float(lines[index+3].split()[4])) )/2.
    print('this is frs:', frs)
    return frs, errs

def runefficiencies(trees, friends, targetdir, fmca, fcut, ftight, fxvar, enabledcuts, disabledcuts, scaleprocesses, compareprocesses, showratio, extraopts = ''):
    
    if not type(trees)==list: trees = [trees]
    treestring = ' '.join(' -P '+ t for t in list(trees))
    cmd  = ' mcEfficiencies.py --s2v -f -j 6 -l {lumi} -o {td} {trees} {fmca} {fcut} {ftight} {fxvar}'.format(lumi=lumi, td=targetdir, trees=treestring, fmca=fmca, fcut=fcut, ftight=ftight, fxvar=fxvar)
    if friends:
        #cmd += ' --Fs {friends}'.format(friends=friends)
        #cmd += ' -F mjvars/t {friends}/friends_evVarFriend_{{cname}}.root --FMC sf/t {friends}/friends_sfFriend_{{cname}}.root  '.format(friends=friends)
        cmd += ' -F Friends {friends}/tree_Friend_{{cname}}.root'.format(friends=friends)
    # not needed here cmd += ' --mcc ttH-multilepton/mcc-eleIdEmu2.txt --mcc dps-ww/mcc-tauveto.txt '
    ## cmd += ' --obj treeProducerWMassEle ' ## the tree is called 'treeProducerWMassEle' not 'tree'
    cmd += ' --groupBy cut '
    if doPUandSF and not '-W ' in extraopts: cmd += ' -W puw2016_nTrueInt_36fb(nTrueInt)*LepGood_effSF[0] '
    cmd += ''.join(' -E ^'+cut for cut in enabledcuts )
    cmd += ''.join(' -X ^'+cut for cut in disabledcuts)
    cmd += ' --compare {procs}'.format(procs=(','.join(compareprocesses)  ))
    if scaleprocesses:
        for proc,scale in scaleprocesses.items():
            cmd += ' --scale-process {proc} {scale} '.format(proc=proc, scale=scale)
    showrat   = ''
    if showratio:
        showrat = ' --showRatio '
    cmd += showrat
    if extraopts:
        cmd += ' '+extraopts

    print 'running: python', cmd
    subprocess.call(['python']+cmd.split())#+['/dev/null'],stderr=subprocess.PIPE)


def runplots(trees, friends, targetdir, fmca, fcut, fplots, enabledcuts, disabledcuts, processes, scaleprocesses, fitdataprocess, plotlist, showratio, extraopts = '', invertedcuts = [], submitit = False, name = ''):
    
    if not type(trees)==list: trees = [trees]
    treestring = ' '.join(' -P '+ t for t in list(trees))
    cmd  = ' mcPlots.py --s2v -f -j 6 -l {lumi} --pdir {td} {trees} {fmca} {fcut} {fplots}'.format(lumi=lumi, td=targetdir, trees=treestring, fmca=fmca, fcut=fcut, fplots=fplots)
    if friends:
        cmd += ' -F Friends {friends}/tree_Friend_{{cname}}.root'.format(friends=friends)
    cmd += ''.join(' -E ^'+cut for cut in enabledcuts )
    cmd += ''.join(' -X ^'+cut for cut in disabledcuts)
    cmd += ' --sP '+','.join(plot for plot in plotlist)
    cmd += ' -p '+','.join(processes)
    if invertedcuts:
        cmd += ''.join(' -I ^'+cut for cut in invertedcuts )
    if doPUandSF and not '-W ' in extraopts: cmd += ' -W puw2016_nTrueInt_36fb(nTrueInt)*LepGood_effSF[0] '
    cmd += ' -o '+targetdir+'/'+'_AND_'.join(plot for plot in plotlist)+'.root'
    if fitdataprocess:
        cmd+= ' --fitData '
        cmd+= ''.join(' --flp '+proc for proc in fitdataprocess)
    if scaleprocesses:
        for proc,scale in scaleprocesses.items():
            cmd += ' --scale-process {proc} {scale} '.format(proc=proc, scale=scale)
    showrat   = ''
    if showratio:
        showrat = ' --showRatio '
    cmd += showrat
    if extraopts:
        cmd += ' '+extraopts

    if not submitit:
        print 'running: python', cmd
        subprocess.call(['python']+cmd.split())#+['/dev/null'],stderr=subprocess.PIPE)
    else:
        submitIt(targetdir, name, 'python '+cmd, False)

def simplePlot():
    print '=========================================='
    print 'running simple plots'
    print '=========================================='
    #trees     = ['/eos/cms/store/group/phys_tracking/elisabetta/WSkims/']
    #trees     = ['/eos/user/m/mdunser/w-helicity-13TeV/trees/trees_all_skims/']
    trees     = ['/eos/user/m/mdunser/w-helicity-13TeV/trees/trees_all_skims/']
    #friends   = '/eos/user/m/mdunser/w-helicity-13TeV/friends/friends_SFs_pu_awayJet-2017-12-11/'
    friends   = '/eos/user/m/mdunser/w-helicity-13TeV/trees/trees_all_skims/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/simple_plots/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )

    fmca      = 'w-helicity-13TeV/wmass_mu/simple/mca_simple.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/simple/cuts_simple.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/simple/plots.txt'

    enable    = []
    disable   = []
    #processes = ['data', 'Z', 'W', 'fakes_data', 'Top', 'DiBosons']
    processes = ['WplusNoSkim']
    fittodata = []
    scalethem = {}
    extraopts = '  ' #--maxRatioRange 0.8 1.2 --fixRatioRange ' #'--plotmode=norm '
    makeplots = ['weightLongPlus', 'weightLeftPlus', 'weightRightPlus'] #'mtl1tk', 'etal1', 'ptl1']#'nVert', 'ptl1', 'etal1', 'mtl1tk', 'mtl1pf', 'tkmet', 'pfmet']
    showratio = False
    runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)
    
def makePDFvariations():
    print '=========================================='
    print 'running pdf variations of the abs(Y)'
    print '=========================================='
    trees     = ['/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/']
    friends   = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/absY_pdfVariations/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )

    fmca      = 'w-helicity-13TeV/wmass_mu/mca-includes/mca-80X-wmunu-sig.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/helicityTemplates/cuts.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/helicityTemplates/plots.txt'

    for ch in ['plus', 'minus']:
        for i in range(1,61):
            enable    = []#'recoCuts']
            disable   = []
            processes = ['W{ch}_left'.format(ch=ch), 'W{ch}_right'.format(ch=ch), 'W{ch}_long'.format(ch=ch),]
            fittodata = []
            scalethem = {}
            extraopts = ' --plotmode=nostack -W hessWgt{i} '.format(i=i)
            makeplots = ['w{ch}_wy_pdf{i}'.format(ch=ch,i=i)]
            showratio = False
            runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts, [], True, '{ch}_pdf{i}'.format(ch=ch,i=i))
        extraopts = ' --plotmode=nostack -W 1. '.format(i=i)
        makeplots = ['w{ch}_wy_central'.format(ch=ch)]
        runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts, [])#, True, '{ch}_central'.format(ch=ch))
    
def compareScales():
    print '=========================================='
    print 'comparing W-pT central and qcd scales up/down'
    print '=========================================='
    trees     = ['/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/']
    friends   = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/qcdScales/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )

    fmca      = 'w-helicity-13TeV/wmass_mu/mca-includes/mca-80X-wmunu-sig-forscales.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/helicityTemplates/cuts.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/helicityTemplates/plots.txt'

    for ch in ['both']:#'plus', 'minus', 'both']:
        enable    = ['w'+ch]
        disable   = []
        processes = ['W{ch}_{iv}'.format(ch=ch, iv=i) for i in ['central', 'wptSlopeUp', 'wptSlopeDn' , 'qcdUp', 'qcdDn', 'muRUp', 'muRDn', 'muFUp', 'muFDn'] ]
        fittodata = []
        scalethem = {}
        extraopts = ' --maxRatioRange 0.9 1.1 --fixRatioRange --plotmode=nostack -W 1. --ratioDen W{ch}_central --ratioNums {allp} '.format(ch=ch,allp=','.join(processes) )
        makeplots = ['w{ch}_wpt'.format(ch=ch), 'ptl1', 'etal1']
        showratio = True
        runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts, [])

    ## enable    = ['wboth']
    ## disable   = []
    ## processes = ['Wboth_{iv}'.format(iv=i) for i in ['central', 'qcdUp', 'qcdDn', 'muRUp', 'muRDn', 'muFUp', 'muFDn'] ]
    ## fittodata = []
    ## scalethem = {}
    ## extraopts = ' --maxRatioRange 0.9 1.1 --fixRatioRange --plotmode=nostack -W 1. --ratioDen Wboth_central --ratioNums {allp} '.format(allp=','.join(processes) )
    ## makeplots = ['ptl1', 'etal1']
    ## showratio = True
    ## runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts, [])

    
    
def fakesDataMC():
    print '=========================================='
    print 'running fake closure/validation plots'
    print '=========================================='
    trees     = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/'
    friends   = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/fakes-dataMC/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
    fmca      = 'w-helicity-13TeV/wmass_mu/mca-wmu-helicity.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/cuts_wmu.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/FRfast/plots.txt'

    enable    = []
    disable   = []
    processes = ['data', 'Wincl', 'data_fakes', 'Top', 'DiBosons', 'Z']
    fittodata = []
    scalethem = {}
    extraopts = '  --maxRatioRange 0.8 1.2 --fixRatioRange  --fitData '
    makeplots = ['ptl1', 'etal1', 'mtl1pf']#mtl1pf', 'pfmet']#'ptl1', 'etal1', 'mtl1pf', 'pfmet']
    showratio = True
    runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)

def makeGenRecoEfficiencies(LO):
    print '=========================================='
    print 'making the unfolding efficiencies from gen to reco'
    print '=========================================='

    fcut      = 'w-helicity-13TeV/wmass_mu/helicityTemplates/cuts.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/helicityTemplates/plots.txt'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/unfoldingGenRecoEfficiencies/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )

    if LO:
        trees     = '/eos/cms/store/group/dpg_ecal/comm_ecal/localreco/TREES_1LEP_80X_V3_NoSkim4/'
        friends   = trees+'/friends/'
        fmca      = 'w-helicity-13TeV/wmass_mu/mca-includes/mca-80X-wmunu-sig-LO.txt'

    else:
        trees     = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/'
        friends   = trees+'/friends/'
        fmca      = 'w-helicity-13TeV/wmass_mu/mca-includes/mca-80X-wmunu-sig.txt'

    for ch in ['plus', 'minus']:
        processes = ['W{c}_left'.format(c=ch), 'W{c}_right'.format(c=ch), 'W{c}_long'.format(c=ch)]
        disable   = []
        fittodata = []
        scalethem = {}
    
        for rg in ['reco', 'gen']:
            if rg == 'reco':
                enable = ['w'+ch, 'recoCuts']
                extraopts = ' -W puw2016_nTrueInt_36fb(nTrueInt)*LepGood_effSF[0] --plotmode=nostack'
            else:
                enable = ['w'+ch]
                extraopts = ' -W 1.0 --plotmode=nostack' ## don't use lepSF for GEN, but use puW
    
            makeplots = ['w{ch}_wy{r}'.format(ch=ch,r='_reco' if rg == 'reco' else '')]

            if LO:
                makeplots = [i+'_LO' for i in makeplots]
    
            showratio = False
            runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)
    
def fractionReweighting():
    print '=========================================='
    print 'running templates for signal or background '
    print '=========================================='

    doSignal = True

    if doSignal:
        trees     = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/'
        friends   = trees+'/friends/'
        targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/helicityTemplates/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
        fmca      = 'w-helicity-13TeV/wmass_mu/mca-includes/mca-80X-wmunu-sig.txt'
        fcut      = 'w-helicity-13TeV/wmass_mu/helicityTemplates/cuts.txt'
        fplots    = 'w-helicity-13TeV/wmass_mu/helicityTemplates/plots.txt'

        for ch in ['plus', 'minus']:
            enable    = ['w'+ch]
            disable   = []
            processes = ['W{c}_left'.format(c=ch), 'W{c}_right'.format(c=ch), 'W{c}_long'.format(c=ch)]
            fittodata = []
            scalethem = {}
            makeplots = ['w{ch}_wyVsEta'.format(ch=ch)]#, 'etaPt', 'etaPtYgen', 'mtwtk', 'etal1', 'ptl1', 'etal1gen', 'ptl1gen', 'wpt']#, 'etaPtY']
            extraopts = ' -W 1. --plotmode=nostack'

            showratio = False
            runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)
    else:
        trees     = ['/eos/user/m/mdunser/w-helicity-13TeV/trees/trees_all_skims/']
        friends   =  '/eos/user/m/mdunser/w-helicity-13TeV/trees/trees_all_skims/friends/'
        targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/templates-bkg/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
        fmca      = 'w-helicity-13TeV/wmass_mu/mca-wmu-helicity.txt'
        fcut      = 'w-helicity-13TeV/wmass_mu/cuts_simple.txt'
        fplots    = 'w-helicity-13TeV/wmass_mu/simple/plots.txt'

        enable    = []
        disable   = []
        processes = ['data_fakes', 'Top', 'Z', 'DiBosons', 'QCD']
        fittodata = []
        scalethem = {}
        extraopts = ' -W 1. --plotmode=nostack '
        makeplots = ['etaPt']

        showratio = False
        runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)
    
def dyComparison():
    print '=========================================='
    print 'running checks on DY '
    print '=========================================='
    trees     = ['/eos/cms/store/group/phys_tracking/elisabetta/WSkims/']
    friends   = '/eos/user/m/mdunser/w-helicity-13TeV/friends/friends_SFs_pu_awayJet-2017-12-11/'#2017-12-01/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/dy-dataMC/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
    fmca      = 'w-helicity-13TeV/wmass_mu/dy/mca.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/dy/cuts.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/dy/plots.txt'

    enable    = []
    disable   = []
    processes = ['data', 'Z']## very small:, 'Top', 'DiBosons']
    fittodata = []
    scalethem = {}
    extraopts = ' -W LepGood_effSF[0]*LepGood_effSF[1] --maxRatioRange 0.8 1.2 --fixRatioRange '# --maxRatioRange 0. 2. --fixRatioRange  '
    makeplots = ['rho', 'nVert']#'etal2']#, 'ptl1', 'etal1', 'ptl2', 'mll']#'etal2', 'nVert', 'mll', 'tkmet', 'pfmet']
    showratio = True
    runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)

def muonFlipRate():
    print '=========================================='
    print 'running checks on DY '
    print '=========================================='
    trees     = '/eos/cms/store/group/dpg_ecal/comm_ecal/localreco/TREES_1LEP_80X_V3/'
    friends   = trees+'/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/fliprate-muon/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
    fmca      = 'w-helicity-13TeV/wmass_mu/dy/mca.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/dy/cuts.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/dy/plots.txt'

    enable    = []
    disable   = []
    processes = ['Z', 'data']
    fittodata = []
    scalethem = {}
    extraopts = ' -A alwaystrue samesign LepGood1_pdgId*LepGood2_pdgId==169 '
    makeplots = ['mll']
    showratio = True
    runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts)

def flipTests():
    print '=========================================='
    print 'running some muon flip tests'
    print '=========================================='
    trees     = '/eos/cms/store/group/dpg_ecal/comm_ecal/localreco/TREES_1LEP_80X_V3_NoSkim5/'
    friends   = trees+'/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/muon-flips/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
    fmca      = 'w-helicity-13TeV/wmass_mu/mca-includes/mca-80X-wmunu-sigincl.txt'
    fcut      = 'w-helicity-13TeV/wmass_mu/cuts_wmu.txt'
    fplots    = 'w-helicity-13TeV/wmass_mu/simple/plots.txt'

    enable    = []
    disable   = []
    invert    = []
    processes = ['Wincl']
    fittodata = []
    scalethem = {}
    extraopts = ' -A  mtl1pf40 flips LepGood1_mcMatchId*LepGood1_charge<0  -A alwaystrue tightChargeFix LepGood1_tightChargeFix==2 -A alwaystrue Wmuondecay abs(genw_decayId)==14 '
    makeplots = ['ptVsEta']
    showratio = False
    runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts, invert)

    
def fakeShapes():
    print '=========================================='
    print 'running fake shape plots'
    print '=========================================='
    trees     = ['/afs/cern.ch/work/m/mdunser/public/wHelicityTrees/TREES_1LEP_53X_V2/']
    friends   = '/eos/cms/store/cmst3/group/susy/emanuele/wmass/trees/TREES_1LEP_53X_V2/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/fakes-sanity/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )
    fmca      = 'w-helicity/FR/mca_fr_closure.txt'
    fcut      = 'w-helicity/FR/cuts_fr_closure.txt'
    fplots    = 'w-helicity/FR/plots_fr_closure.txt'

    enable    = []
    disable   = ['muonTightIso']
    invert    = []
    processes = ['data', 'wjets', 'qcd', 'singleTop', 'ttjets', 'diboson', 'dyjets']
    fittodata = ['qcd']
    scalethem = {}
    extraopts = ' --maxRatioRange 0. 2. '
    makeplots = ['l1reliso03',]# 'mtl1tk', 'pfmet', 'ptl1', 'etal1']
    showratio = True
    runplots(trees, friends, targetdir, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, makeplots, showratio, extraopts, invert)



def makeFakeRatesFast(recalculate):
    trees     = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/'
    friends   = '/eos/user/m/mdunser/w-helicity-13TeV/trees/TREES_latest_1muskim/friends/'
    targetdir = '/afs/cern.ch/user/m/mdunser/www/private/w-helicity-13TeV/fakerates/{date}{pf}/'.format(date=date, pf=('-'+postfix if postfix else '') )

    fmca   = 'w-helicity-13TeV/wmass_mu/FRfast/mca_fr.txt' 
    fcut   = 'w-helicity-13TeV/wmass_mu/FRfast/cuts_fr.txt'
    fplots = 'w-helicity-13TeV/wmass_mu/FRfast/plots.txt'       
    ftight = 'w-helicity-13TeV/wmass_mu/FRfast/tightCut.txt'    
    processes = ['QCD', 'WandZ', 'data']
    compprocs = ['QCD', 'WandZ', 'data', 'data_sub']
    fittodata = ['QCD', 'WandZ']
    makeplots = ['mtl1pf', 'reliso03'] ## the first plot here is the one from which the scale factors are derived!!!
    
    import sys
    sys.path.append('w-helicity-13TeV/wmass_mu/')
    import make_cards_mu
    
    #binning = [25,30,35,40,50,100] ## from xvars.txt
    binning = [25,27,29,31,33,35,37,39,41,43,45,48,51,54,60,65] ## from xvars.txt
    binningeta = eval(make_cards_mu.etabinning) ## the binning is a list in form of a string
    h_name  = 'fakerate_mu'; h_title = 'fakerates muons'

    h_fakerate_data = ROOT.TH2F(h_name+'_data',h_title+' - data', len(binning)-1, array.array('f',binning), len(binningeta)-1, array.array('f',binningeta))
    h_fakerate_mc   = ROOT.TH2F(h_name+'_qcd' ,h_title+' - qcd' , len(binning)-1, array.array('f',binning), len(binningeta)-1, array.array('f',binningeta))
    h_fakerate_data .Sumw2()
    h_fakerate_mc   .Sumw2()
    h_fakerate_data .GetZaxis().SetRangeUser(0.01,0.45)
    h_fakerate_mc   .GetZaxis().SetRangeUser(0.01,0.45)
    h_fakerate_data .GetXaxis().SetTitle('p_{T} mu'); h_fakerate_data .GetYaxis().SetTitle('#eta mu')
    h_fakerate_mc   .GetXaxis().SetTitle('p_{T} mu'); h_fakerate_mc   .GetYaxis().SetTitle('#eta mu')

    h_name  = 'promptrate_mu'; h_title = 'promptrates muons'
    h_promptrate_data = ROOT.TH2F(h_name+'_data',h_title+' - data', len(binning)-1, array.array('f',binning), len(binningeta)-1, array.array('f',binningeta))
    h_promptrate_mc   = ROOT.TH2F(h_name+'_qcd' ,h_title+' - qcd' , len(binning)-1, array.array('f',binning), len(binningeta)-1, array.array('f',binningeta))
    h_promptrate_data .Sumw2()
    h_promptrate_mc   .Sumw2()
    h_promptrate_data .GetZaxis().SetRangeUser(0.5,1.00)
    h_promptrate_mc   .GetZaxis().SetRangeUser(0.5,1.00)
    h_promptrate_data .GetXaxis().SetTitle('p_{T} mu'); h_promptrate_data .GetYaxis().SetTitle('#eta mu')
    h_promptrate_mc   .GetXaxis().SetTitle('p_{T} mu'); h_promptrate_mc   .GetYaxis().SetTitle('#eta mu')

    ## add MT cut to the eff plot!
    fakerates = {}; promptrates = {}
    scales = {}
    printAggressive('STARTING FAKE RATES...!')
    for j,eta in enumerate(binningeta[:-1]):

        etastring = 'To'.join(str(i).replace('-','m').replace('.','p') for i in [eta, binningeta[j+1]] )
        tmp_td = targetdir+'/'+etastring

        ## this is some weird recursive magic to submit this to the batch
        if opts.submitFR:
            abspath = os.path.abspath('.')
            tmp_cmd = 'python '+abspath+'/runWHelicity_mu_13TeV.py --fr --recalculate --doBin {j}'.format(j=j)
            submitFRrecursive(tmp_td, 'frjob_{j}'.format(j=j), tmp_cmd)
            continue
        if opts.doBin > -1:
            if not j == opts.doBin: continue
        ## end weird magic

        scalethem = {}
        enable    = []
        disable   = ['muonTightIso']
        newplots = [('mu_'+plot) for plot in makeplots]
        extraopts = ' -A alwaystrue ETA{eta} LepGood1_eta>={e1}&&LepGood1_eta<{e2} '.format(eta=etastring, e1=eta, e2=binningeta[j+1]) ## no whitespaces in the cutstring here!!
        extraopts+= ' -W {wgt} '.format(wgt=make_cards_mu.WEIGHTSTRING.replace("'",""))
        if recalculate: runplots(trees, friends, tmp_td, fmca, fcut, fplots, enable, disable, processes, scalethem, fittodata, newplots, True, extraopts)
        printAggressive('DONE MAKING THE PLOTS TO DERIVE THE EWK SCALE FACTORS!')
        scales['qcd_{eta}'  .format(eta=etastring)] = readScaleFactor(tmp_td+'/mu_{plot}.txt'.format(plot=makeplots[0]), 'QCD')
        scales['wandz_{eta}'.format(eta=etastring)] = readScaleFactor(tmp_td+'/mu_{plot}.txt'.format(plot=makeplots[0]), 'WandZ')
        enable  = ['mtl1pf40max']## IMPORTANT
        disable = ['muonTightIso']
        scalethem = {'QCD'  : scales['qcd_{eta}'  .format(eta=etastring)],
                     'WandZ': scales['wandz_{eta}'.format(eta=etastring)]}
        fxvar  = 'w-helicity-13TeV/wmass_mu/FRfast/xvars.txt'
        ## reproduce plots with MT and MET included
        printAggressive('SCALING THE PROCESSES BY FACTORS')
        print scalethem
        if recalculate: runplots(trees, friends, tmp_td+'/mTCutIncluded/', fmca, fcut, fplots, enable, disable, processes, scalethem, [], newplots, True, extraopts) ## don't fit to data anymore
        extraopts += ' --ratioRange 0 2 --sp QCD '
        if recalculate: runefficiencies(trees, friends, tmp_td+'/fr_mu_{eta}'.format(eta=etastring), fmca, fcut, ftight, fxvar, enable, disable, scalethem, compprocs, True, extraopts)
        fakerates['fr_mu_qcd_{eta}'.format(eta=etastring)] = readFakerate(tmp_td+'/fr_mu_{eta}.txt'.format(eta=etastring),'QCD')
        fakerates['fr_mu_dat_{eta}'.format(eta=etastring)] = readFakerate(tmp_td+'/fr_mu_{eta}.txt'.format(eta=etastring),'Data - EWK')

        promptrates['fr_mu_qcd_{eta}'.format(eta=etastring)] = readFakerate(tmp_td+'/fr_mu_{eta}.txt'.format(eta=etastring),'WandZ')
        promptrates['fr_mu_dat_{eta}'.format(eta=etastring)] = readFakerate(tmp_td+'/fr_mu_{eta}.txt'.format(eta=etastring),'WandZ')

        print len(binning), binning
        print len(fakerates['fr_mu_dat_{eta}'.format(eta=etastring)][0]), fakerates['fr_mu_dat_{eta}'.format(eta=etastring)][0]
        for i in range(len(fakerates['fr_mu_dat_{eta}'.format(eta=etastring)][0])):
            h_fakerate_data.SetBinContent(i+1,j+1, fakerates['fr_mu_dat_{eta}'.format(eta=etastring)][0][i])
            h_fakerate_data.SetBinError  (i+1,j+1, fakerates['fr_mu_dat_{eta}'.format(eta=etastring)][1][i])
            h_fakerate_mc  .SetBinContent(i+1,j+1, fakerates['fr_mu_qcd_{eta}'.format(eta=etastring)][0][i])
            h_fakerate_mc  .SetBinError  (i+1,j+1, fakerates['fr_mu_qcd_{eta}'.format(eta=etastring)][1][i])
            h_promptrate_data.SetBinContent(i+1,j+1, promptrates['fr_mu_dat_{eta}'.format(eta=etastring)][0][i])
            h_promptrate_data.SetBinError  (i+1,j+1, promptrates['fr_mu_dat_{eta}'.format(eta=etastring)][1][i])
            h_promptrate_mc  .SetBinContent(i+1,j+1, promptrates['fr_mu_qcd_{eta}'.format(eta=etastring)][0][i])
            h_promptrate_mc  .SetBinError  (i+1,j+1, promptrates['fr_mu_qcd_{eta}'.format(eta=etastring)][1][i])

    if not opts.submitFR and opts.doBin < 0:
        h_fakerate_data_frUp = h_fakerate_data.Clone(h_fakerate_data.GetName()+'_frUp')
        h_fakerate_mc_frUp   = h_fakerate_mc  .Clone(h_fakerate_mc  .GetName()+'_frUp')
        h_fakerate_data_frUp.Scale(1.1)
        h_fakerate_mc_frUp  .Scale(1.1)

        h_fakerate_data_frDn = h_fakerate_data.Clone(h_fakerate_data.GetName()+'_frDn')
        h_fakerate_mc_frDn   = h_fakerate_mc  .Clone(h_fakerate_mc  .GetName()+'_frDn')
        h_fakerate_data_frDn.Scale(0.9)
        h_fakerate_mc_frDn  .Scale(0.9)

        ROOT.gROOT.SetBatch()
        ROOT.gStyle.SetOptStat(0)
        canv = ROOT.TCanvas()
        #canv.SetLogx()
        ROOT.gStyle.SetPaintTextFormat(".3f")
        h_fakerate_data.Draw('colz text45 e')
        canv.SaveAs(targetdir+'fakerate_mu_data_{date}.png'.format(date=date))
        canv.SaveAs(targetdir+'fakerate_mu_data_{date}.pdf'.format(date=date))
        h_fakerate_mc  .Draw('colz text45 e')
        canv.SaveAs(targetdir+'fakerate_mu_qcd_{date}.png'.format(date=date))
        canv.SaveAs(targetdir+'fakerate_mu_qcd_{date}.pdf'.format(date=date))
        h_promptrate_data.Draw('colz text45 e')
        canv.SaveAs(targetdir+'promptrate_mu_data_{date}.png'.format(date=date))
        canv.SaveAs(targetdir+'promptrate_mu_data_{date}.pdf'.format(date=date))
        h_promptrate_mc  .Draw('colz text45 e')
        canv.SaveAs(targetdir+'promptrate_mu_qcd_{date}.png'.format(date=date))
        canv.SaveAs(targetdir+'promptrate_mu_qcd_{date}.pdf'.format(date=date))
        outfile = ROOT.TFile('w-helicity-13TeV/wmass_mu/fakerateMap_mu_{date}{pf}.root'.format(date=date,pf=('_'+postfix if postfix else '')),'RECREATE')
        h_fakerate_data.Write()
        h_fakerate_mc  .Write()
        h_fakerate_data_frUp.Write()
        h_fakerate_mc_frUp  .Write()
        h_fakerate_data_frDn.Write()
        h_fakerate_mc_frDn  .Write()
        outfile.Close()

        outfile = ROOT.TFile('w-helicity-13TeV/wmass_mu/promptrateMap_mu_{date}{pf}.root'.format(date=date,pf=('_'+postfix if postfix else '')),'RECREATE')
        h_promptrate_data.Write()
        h_promptrate_mc  .Write()
        #h_promptrate_data_frUp.Write()
        #h_promptrate_mc_frUp  .Write()
        #h_promptrate_data_frDn.Write()
        #h_promptrate_mc_frDn  .Write()
        outfile.Close()
        
        print scales
        print fakerates
        print promptrates

        h_fr_smoothed_data = ROOT.TH2F('fakerates_smoothed_data'  ,' fakerates - smoothed data'  , len(binningeta)-1, array.array('f',binningeta), 2, array.array('f',[0., 1., 2.]))
        h_pr_smoothed_data = ROOT.TH2F('promptrates_smoothed_data',' promptrates - smoothed data', len(binningeta)-1, array.array('f',binningeta), 2, array.array('f',[0., 1., 2.]))
        #h_fr_smoothed_mc   = ROOT.TH2F(h_name+'_qcd' ,h_title+' - qcd' , len(binning)-1, array.array('f',binning), len(binningeta)-1, array.array('f',binningeta))



        for j,eta in enumerate(binningeta[:-1]):


            print 'GETTING AND FITTING THE FR FROM', etastring

            etastring = 'To'.join(str(i).replace('-','m').replace('.','p') for i in [eta, binningeta[j+1]] )
            tmp_td = targetdir+'/'+etastring

            graph_file= ROOT.TFile(tmp_td+'/fr_mu_{eta}'.format(eta=etastring), 'read')

            mg = ROOT.TMultiGraph(); pols = []
            for rate in ['pr', 'fr']:

                pol0 = ROOT.TF1("{r}_pol0_{eta}".format(r=rate,eta=etastring), "[0]        ", 25., 50.)
                pol1 = ROOT.TF1("{r}_pol1_{eta}".format(r=rate,eta=etastring), "[1]*x + [0]", 25., 50.)


                if rate == 'fr':
                    graph = graph_file.Get('muonTightIso_pt_fine_binned_data_sub')
                    pol0.SetLineColor(ROOT.kGreen); pol0.SetLineWidth(2)
                    pol1.SetLineColor(ROOT.kRed-3); pol1.SetLineWidth(2)
                    pol0.SetParLimits(1, 0.1, 0.4)
                    pol1.SetParLimits(1, -0.1  , 0.1)
                    pol1.SetParLimits(0,  0.1  , 1.1)

                else:
                    graph = graph_file.Get('muonTightIso_pt_fine_binned_WandZ')
                    graph.SetLineColor(ROOT.kRed); graph.SetMarkerColor(ROOT.kRed)
                    pol0.SetLineColor(ROOT.kBlue)   ; pol0.SetLineWidth(2)
                    pol1.SetLineColor(ROOT.kAzure-3); pol1.SetLineWidth(2)
                    pol0.SetParLimits(1, 0.1, 1.1)
                    pol1.SetParLimits(1, -0.1  , 0.1)
                    pol1.SetParLimits(0,  0.1  , 1.1)

                mg.Add(copy.deepcopy(graph))

                graph.Fit("{r}_pol0_{eta}".format(r=rate,eta=etastring), "M", "", 25., 50.)
                graph.Fit("{r}_pol1_{eta}".format(r=rate,eta=etastring), "M", "", 25., 50.)

                pol0_chi2 = pol0.GetChisquare(); pol0_ndf = pol0.GetNDF()
                pol1_chi2 = pol1.GetChisquare(); pol1_ndf = pol1.GetNDF()

                rchi2_0 = pol0_chi2/pol0_ndf
                rchi2_1 = pol1_chi2/pol1_ndf

                bestfunc = pol0 if rchi2_0 < rchi2_1 else pol1
                worstfun = pol0 if rchi2_0 > rchi2_1 else pol1

                print '{r} and {eta}: chi2 of pol0 = {chi0}/{ndf0} = {red0}'.format(r=rate,eta=etastring,chi0=pol0_chi2,ndf0=pol0_ndf, red0=rchi2_0)
                print '{r} and {eta}: chi2 of pol1 = {chi1}/{ndf1} = {red1}'.format(r=rate,eta=etastring,chi1=pol1_chi2,ndf1=pol1_ndf, red1=rchi2_1)

                print 'the better function is {func}'.format(func=bestfunc.GetName())

                #print '{eta}: compared to {func}         .   value={val:.3f}'.format(eta=eta, func = worstfun.GetName(), val=worstfun.GetChisquare()/worstfun.GetNDF())
                
                etabin = j+1 #if eta == 'barrel' else 2
                
                if rate == 'fr':
                    h_fr_smoothed_data.SetBinContent(etabin, 1, bestfunc.GetParameter(0))
                    h_fr_smoothed_data.SetBinError  (etabin, 1, bestfunc.GetParError (0))

                    h_fr_smoothed_data.SetBinContent(etabin, 2, bestfunc.GetParameter(1) if bestfunc.GetNpar() > 1 else 0.)
                    h_fr_smoothed_data.SetBinError  (etabin, 2, bestfunc.GetParError (1) if bestfunc.GetNpar() > 1 else 0.)

                else:
                    h_pr_smoothed_data.SetBinContent(etabin, 1, bestfunc.GetParameter(0))
                    h_pr_smoothed_data.SetBinError  (etabin, 1, bestfunc.GetParError (0))

                    h_pr_smoothed_data.SetBinContent(etabin, 2, bestfunc.GetParameter(1) if bestfunc.GetNpar() > 1 else 0.)
                    h_pr_smoothed_data.SetBinError  (etabin, 2, bestfunc.GetParError (1) if bestfunc.GetNpar() > 1 else 0.)

                pols.append(copy.deepcopy(pol0))
                pols.append(copy.deepcopy(pol1))
                mg.Add(copy.deepcopy(graph))

            #graph.Draw('ape')
            mg.Draw('ape')
            mg.GetYaxis().SetRangeUser(0., 1.0)
            for p in pols:
                p.Draw('same')
            ##pol1.Draw('same')
            canv.SaveAs(targetdir+'fakeAndPromptRate_fit_data_{eta}.png'.format(eta=etastring))
            canv.SaveAs(targetdir+'fakeAndPromptRate_fit_data_{eta}.pdf'.format(eta=etastring))
        
        h_fr_smoothed_data.Draw("colz text45")
        h_fr_smoothed_data.GetZaxis().SetRangeUser(-0.05, 0.45)
        h_fr_smoothed_data.GetXaxis().SetTitle('#eta_{#mu}')
        h_fr_smoothed_data.GetXaxis().SetTitleSize(0.045)
        h_fr_smoothed_data.GetXaxis().SetLabelSize(0.05)
        h_fr_smoothed_data.GetYaxis().SetLabelSize(0.08)
        h_fr_smoothed_data.GetYaxis().SetBinLabel(1, 'offset')
        h_fr_smoothed_data.GetYaxis().SetBinLabel(2, 'slope')
        canv.SaveAs(targetdir+'fakerate_smoothed_data_{date}.png'.format(date=date))
        canv.SaveAs(targetdir+'fakerate_smoothed_data_{date}.pdf'.format(date=date))
        
        h_pr_smoothed_data.Draw("colz text45")
        h_pr_smoothed_data.GetZaxis().SetRangeUser(0.00, 1.0)
        h_pr_smoothed_data.GetXaxis().SetTitle('#eta_{#mu}')
        h_pr_smoothed_data.GetXaxis().SetTitleSize(0.045)
        h_pr_smoothed_data.GetXaxis().SetLabelSize(0.05)
        h_pr_smoothed_data.GetYaxis().SetLabelSize(0.08)
        h_pr_smoothed_data.GetYaxis().SetBinLabel(1, 'offset')
        h_pr_smoothed_data.GetYaxis().SetBinLabel(2, 'slope')
        canv.SaveAs(targetdir+'promptrate_smoothed_data_{date}.png'.format(date=date))
        canv.SaveAs(targetdir+'promptrate_smoothed_data_{date}.pdf'.format(date=date))
        
        outfile = ROOT.TFile('w-helicity-13TeV/wmass_mu/frAndPr_fit_mu_{date}{pf}.root'.format(date=date,pf=('_'+postfix if postfix else '')),'RECREATE')
        h_fr_smoothed_data.Write()
        h_pr_smoothed_data.Write()
        outfile.Close()
    

        #python mcEfficiencies.py -f -j 4 -l $TRIGLUMI --s2v -P $ELFRTREES dps-ww/elFR/mca_elFR.txt dps-ww/elFR/cuts_elFR.txt dps-ww/elFR/tightCut.txt dps-ww/elFR/xvar${pt}.txt --sp QCD --scale-process QCD $QCDSCALE --scale-process WandZ $WZSCALE -o ~/www/private/dps-ww/${DATE}-elFR${POSTFIX}/${eta}_${pt}/fr_el_${eta}_${pt} --groupBy cut --compare QCD,data,data_sub,total,WandZ --showRatio --ratioRange 0 3 --mcc ttH-multilepton/mcc-eleIdEmu2.txt -X pt${negpt} -X eta${negeta} -X lepMVAtight ;# --sP lpt${pt} # -E mtw1 


if __name__ == '__main__':
    parser = optparse.OptionParser(usage='usage: %prog [opts] ', version='%prog 1.0')
    parser.add_option('--pf'        , '--postfix'    , dest='postfix'      , type='string'       , default=''    , help='postfix for running each module')
    parser.add_option('-d'          , '--date'       , dest='date'         , type='string'       , default=''    , help='run with specified date instead of today')
    parser.add_option('-l'          , '--lumi'       , dest='lumi'         , type='float'        , default=0.    , help='change lumi by hand')
    parser.add_option('--simple'    ,                  dest='simple'       , action='store_true' , default=False , help='make simple plot')
    parser.add_option('--sFR'       ,                  dest='sFR'          , action='store_true' , default=False , help='make simple FR plots')
    parser.add_option('--fr'        , '--fakerates'  , dest='runFR'        , action='store_true' , default=False , help='run fakerates for muons')
    parser.add_option('--rec'       , '--recalculate'  , dest='recalculate'        , action='store_true' , default=False , help='recalculate fakerates')
    parser.add_option('--submitFR'  , '--submitFR'  , dest='submitFR'        , action='store_true' , default=False , help='submit the fakerates to the batch')
    parser.add_option('--doBin'     ,                 dest='doBin'         , type='int', default=-999 , help='submit exactly this bin of the FR calculation to the batch')
    parser.add_option('--pr'        , '--promptrates', dest='runPR'        , action='store_true' , default=False , help='run promptrates for muons')
    parser.add_option('--fs'        , '--fakeshapes' , dest='fakeShapes'   , action='store_true' , default=False , help='run fake shapes')
    parser.add_option('--fc'        , '--fakeclosure', dest='fakeClosure'   , action='store_true' , default=False , help='run fake closure')
    parser.add_option('--fdm'       , '--fakesDataMC', dest='fakesDataMC'   , action='store_true' , default=False , help='run fakes data MC comparison')
    parser.add_option('--mt'        , '--makeTemplates', dest='makeTemplates', action='store_true' , default=False , help='make templates')
    parser.add_option('--dy'        , '--dyComparison' , dest='dyComparison' , action='store_true' , default=False , help='make dy comparisons')
    parser.add_option('--pdf'       , '--pdfVariations', dest='pdfVariations', action='store_true' , default=False , help='make plots with pdf variations')
    parser.add_option('--unfold'    , '--unfoldEffs'   , dest='unfoldEff'    , action='store_true' , default=False , help='make unfolding efficiencies gen-reco')
    parser.add_option('--unfoldLO'    , '--unfoldLO'   , dest='unfoldLO'    , action='store_true' , default=False , help='make unfolding for LO')
    parser.add_option('--compareScales', '--scales'   , dest='compareScales'    , action='store_true' , default=False , help='compare qcd scales')
    (opts, args) = parser.parse_args()

    global date, postfix, lumi, date
    postfix = opts.postfix
    lumi = 36.0 if not opts.lumi else opts.lumi
    date = datetime.date.today().isoformat()
    if opts.date:
        date = opts.date

    if opts.simple:
        print 'making simple plots'
        simplePlot()
    if opts.sFR:
        print 'making simple FR plots'
        simpleFRPlot()
    if opts.runFR:
        print 'running the fakerates for muons'
        makeFakeRatesFast(opts.recalculate)
    if opts.runPR:
        print 'running the promptrates for muons'
        makePromptRates()
    if opts.fakeShapes:
        print 'running the fakeshapes for muons'
        fakeShapes()
    if opts.fakeClosure:
        print 'running the fakes closure for muons'
        fakeClosure()
    if opts.fakesDataMC:
        print 'running the fakes data-mc comparison'
        fakesDataMC()
    if opts.makeTemplates:
        print 'make helicity templates'
        fractionReweighting()
    if opts.dyComparison:
        print 'running the dy comparisons'
        dyComparison()
    if opts.pdfVariations:
        print 'making pdf variations'
        makePDFvariations()
    if opts.unfoldEff:
        print 'making unfolding efficiencies'
        makeGenRecoEfficiencies(opts.unfoldLO)
    if opts.compareScales:
        print 'making comparison of qcd scales'
        compareScales()
