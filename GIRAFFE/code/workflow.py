#This is a Nipype generator. Warning, here be dragons.
#!/usr/bin/env python

import sys
import nipype
import nipype.pipeline as pe

import nipype.interfaces.io as io
import nipype.interfaces.fsl as fsl
import nipype.algorithms.confounds as confounds
import nipype.interfaces.utility as utility

#Generic datagrabber module that wraps around glob in an
my_io_S3DataGrabber = pe.Node(io.S3DataGrabber(outfields=["outfiles"]), name = 'my_io_S3DataGrabber')
my_io_S3DataGrabber.inputs.bucket = 'openneuro'
my_io_S3DataGrabber.inputs.sort_filelist = True
my_io_S3DataGrabber.inputs.template = 'sub-01/func/sub-01_task-simon_run-1_bold.nii.gz'
my_io_S3DataGrabber.inputs.anon = True
my_io_S3DataGrabber.inputs.bucket_path = 'ds000101/ds000101_R2.0.0/uncompressed/'
my_io_S3DataGrabber.inputs.local_directory = '/tmp'

#Wraps command **slicetimer**
my_fsl_SliceTimer = pe.Node(interface = fsl.SliceTimer(), name='my_fsl_SliceTimer', iterfield = [''])

#Wraps command **mcflirt**
my_fsl_MCFLIRT = pe.Node(interface = fsl.MCFLIRT(), name='my_fsl_MCFLIRT', iterfield = [''])

#Computes the time-course SNR for a time series
my_confounds_TSNR = pe.Node(interface = confounds.TSNR(), name='my_confounds_TSNR', iterfield = [''])
my_confounds_TSNR.inputs.regress_poly = 3

#Wraps command **fslstats**
my_fsl_ImageStats = pe.Node(interface = fsl.ImageStats(), name='my_fsl_ImageStats', iterfield = [''])
my_fsl_ImageStats.inputs.op_string = '-p 98'

#Wraps command **fslmaths**
my_fsl_Threshold = pe.Node(interface = fsl.Threshold(), name='my_fsl_Threshold', iterfield = [''])
my_fsl_Threshold.inputs.args = '-bin'

#Anatomical compcor: for inputs and outputs, see CompCor.
my_confounds_ACompCor = pe.Node(interface = confounds.ACompCor(), name='my_confounds_ACompCor', iterfield = [''])
my_confounds_ACompCor.inputs.num_components = 2

#Wraps command **fsl_regfilt**
my_fsl_FilterRegressor = pe.Node(interface = fsl.FilterRegressor(), name='my_fsl_FilterRegressor', iterfield = [''])
my_fsl_FilterRegressor.inputs.filter_columns = [1, 2]

#Wraps command **fslmaths**
my_fsl_TemporalFilter = pe.Node(interface = fsl.TemporalFilter(), name='my_fsl_TemporalFilter', iterfield = [''])
my_fsl_TemporalFilter.inputs.highpass_sigma = 25

#Change the name of a file based on a mapped format string.
my_utility_Rename = pe.Node(interface = utility.Rename(), name='my_utility_Rename', iterfield = [''])
my_utility_Rename.inputs.format_string = "/output/filteredData.nii.gz"

#Create a workflow to connect all those nodes
analysisflow = nipype.Workflow('MyWorkflow')
analysisflow.connect(my_io_S3DataGrabber, "outfiles", my_fsl_SliceTimer, "in_file")
analysisflow.connect(my_fsl_SliceTimer, "slice_time_corrected_file", my_fsl_MCFLIRT, "in_file")
analysisflow.connect(my_fsl_MCFLIRT, "out_file", my_confounds_TSNR, "in_file")
analysisflow.connect(my_confounds_TSNR, "stddev_file", my_fsl_ImageStats, "in_file")
analysisflow.connect(my_fsl_ImageStats, "out_stat", my_fsl_Threshold, "thresh")
analysisflow.connect(my_fsl_MCFLIRT, "out_file", my_confounds_ACompCor, "realigned_file")
analysisflow.connect(my_fsl_Threshold, "out_file", my_confounds_ACompCor, "mask_files")
analysisflow.connect(my_confounds_ACompCor, "components_file", my_fsl_FilterRegressor, "design_file")
analysisflow.connect(my_confounds_TSNR, "detrended_file", my_fsl_FilterRegressor, "in_file")
analysisflow.connect(my_fsl_FilterRegressor, "out_file", my_fsl_TemporalFilter, "in_file")
analysisflow.connect(my_confounds_TSNR, "stddev_file", my_fsl_Threshold, "in_file")
analysisflow.connect(my_fsl_TemporalFilter, "out_file", my_utility_Rename, "in_file")

#Run the workflow
plugin = 'MultiProc' #adjust your desired plugin here
plugin_args = {'n_procs': 1} #adjust to your number of cores
analysisflow.write_graph(graph2use='flat', format='png', simple_form=False)
analysisflow.run(plugin=plugin, plugin_args=plugin_args)
