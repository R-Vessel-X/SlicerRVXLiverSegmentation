# RVesselX Slicer Liver Anatomy Annotation Plugin

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/1.png" width="800"/>

[![DOI](https://zenodo.org/badge/382068737.svg)](https://zenodo.org/badge/latestdoi/382068737)

## Table of contents

* [Introduction](#Introduction)
* [Using the Plugin](#Using-the-Plugin)
    * [Video tutorials](#Video-tutorials)
    * [Installing the plugin](#Installing-the-plugin)
    * [Plugin Overview](#Plugin-Overview)
    * [Sample Data](#Sample-Data)
    * [Data import and visualization](#Data-import-and-visualization)
    * [Liver segmentation](#Liver-segmentation)
        * [Liver segmentation for MRI data](#Liver-segmentation-for-MRI-data)
        * [Liver segmentation for CT data](#Liver-segmentation-for-CT-data)
    * [Portal veins segmentation](#Portal-veins-segmentation)
        * [Constructing the portal tree](#Constructing-the-portal-tree)
        * [Extracting and segmenting the portal tree](#Extracting-and-segmenting-the-portal-tree)
        * [Editing the portal tree](#Editing-the-portal-tree)
        * [Splitting the portal tree](#Splitting-the-portal-tree)
    * [IVC veins segmentation](#IVC-veins-segmentation)
        * [Constructing the IVC tree](#Constructing-the-IVC-tree)
        * [Extracting and segmenting the IVC tree](#Extracting-and-segmenting-the-IVC-tree)
        * [Editing the IVC tree](#Editing-the-IVC-tree)
    * [Tumor segmentation](#Tumor-segmentation)
    * [Exporting the results](#Exporting-the-results)
* [Developers](#Developers)
    * [Manually installing the plugin](#Manually-installing-the-plugin)
    * [Testing](#Testing)
    * [Contributing](#Contributing)

## Introduction

<div style="text-align:center">
<img class="center" src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/RVXLiverSegmentation/Resources/Icons/RVXLiverSegmentation.png"/>
</div>

The RVesselX slicer plugin is a plugin for Slicer3D which aims at easing the segmentation of liver, liver vessels and
liver tumor from DICOM data for annotation purposes. The exported segmentations will then be used in research.

The plugin provides a systematic annotation workflow and tools to allow for fast segmentation. The plugin is separated
in the following tabs :

* Liver segmentation : Segmentation editor configured for liver segmentation
* Portal veins segmentation: VMTK extension used for portal vein segmentation
* Inferior cava vein segmentation : VMTK extension used for IVC vein segmentation
* Tumor segmentation : Segmentation editor configure for tumor segmentation

At the end of the workflow, the annotated data can be saved to a given output directory.

For more information on the R-Vessel-X project, please visit :  
https://anr.fr/Projet-ANR-18-CE45-0018

## Using the Plugin

### Video tutorials

The following videos outline the different steps to install and use the plugin.
For more detailed explanations, please refer to each section.

* [Installing the extension](https://youtu.be/KQtNxKB3dvc)
* [MRI Liver segmentation](https://youtu.be/tUtT1Om-eqQ)
* [AI CT Liver segmentation](https://youtu.be/CSYJedE4Jnk)
* [Portal veins segmentation](https://youtu.be/YIiysCpyAFk)
* [IVC veins segmentation](https://youtu.be/CQBgRsky-wA)
* [Exporting the results](https://youtu.be/5uvCQUqPeq4)


### Installing the plugin

The plugin can be installed in Slicer3D using
the [extension manager]( https://slicer.readthedocs.io/en/latest/user_guide/extensions_manager.html#install-extensions).
It can be found using the search bar by typing "RVesselX".

When first installing the plugin the following extensions will be installed as well :

* SegmentEditorExtraEffects
* SlicerVMTL
* MarkupsToModel
* PyTorch

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/install_dependencies.png" width="800"/>

After installing the extension, Slicer will have to be restarted for the module to be accessible.
After Slicer has been restarted, the module can be found using the module finder under the name "RVX Liver Segmentation"
.
It can also be found by navigating the module list and clicking on `Segmentation>RVX Liver Segmentation` module.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/install_finding_the_module.png" width="800"/>

After the module is first installed, additional Python libraries will have to be installed.
The libraries will be installed automatically by clicking on the `Download Dependencies and restart` button.
The library will be downloaded from `Python pip` and installed automatically.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/install_python_dependencies.png" width="800"/>

### Plugin Overview

The plugin is built upon the following tabs : Data, Liver, Portal Veins, Portal Veins Edit, IVC Veins, IVC Veins Edit,
Tumors. Navigation between tabs is done either using the arrow buttons at the top of the plugin or by directly clicking
on the tabs.

Each tab is oriented towards one part of the segmentation workflow but can work independently of the other tabs.

* The Liver tab allows to segment the full liver volume
* The Portal Veins and Portal Edit tabs allow to segment the portal veins of the liver
* The ICV Veins and IVC Veins Edit tabs allow to segment the Inferior Cavae Veins of the liver
* The tumors tab allows to segment any tumor present in the liver volume. As this tab is the last of the workflow, it
  also allows to export the results of the previous tabs.

### Sample Data

To test the plugin, the `3D_IRCAD_B_5_Liver` data can be loaded from the Sample Data module. To properly load the data
in the plugin, it is advised to first open the plugin and afterwards to navigate to the Sample module and to load the
data.

This data is extracted from the 3D-IRCADb (3D Image Reconstruction for Comparison of Algorithm Database) database. The
content of 3D-IRCADb is subject to a CC Attribution-Non commercial-No Derivative Works 3.0 licence.

For more information on the IRCAD Database please visit : https://www.ircad.fr/research/3dircadb/

### Data import and visualization

The `Data Tab` is used to open the patient data. Loading can be done using the `Load DICOM` and the `Load Data` buttons.
The input volume needs to be selected using the `Volume` combo box.

The `Data Tab` aggregates the functionalities of the `load Data` and `load DICOM` buttons as well as the `Volume`
and `Volume Rendering` modules for volume display customization.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/data_tab.png" width="800"/>

To start working on the segmentation :

* Click one of `Load DICOM` or `Load Data` and select the data you want to work on.
* Once the volume is loaded in the 2D and 3D view, you can click on the `Liver` tab to proceed with the liver
  segmentation.

### Liver segmentation

The `Liver Tab` is used to segment the liver volume. Two segments are created by default, the `Liver In` and `Liver Out`
segments.

The `Segment CT Liver` segmentation effect is also available for fast segmentation of the liver for CT data. This
segmentation effect is built upon MONAI and PyTorch to provide ML accelerated segmentation for CT data.

#### Liver segmentation for MRI data

To segmentation of the liver for MRI data can be done using the following process:

* Select the `Liver In` segment and start painting in the liver. To improve the painting speed, you can choose a 3D
  brush.
* Select the `Liver Out` segment and paint outside the liver.
* Select the `Grow from seeds` and click on the initialize button
* Iterate on the `In` and `Out` segments until the grow from seeds is satisfying
* Apply the `Grow from seeds` segmentation
* Use the `Scissors` tool to remove any undesired volumes
* Use the `Margin` tool by growing and shrinking back the volume to improve the outside shape of the volume
* Use the `Smoothing` tool to smooth out the volume

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/liver_tab.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/liver_tab_result.png" width="800"/>

#### Liver segmentation for CT data

To segmentation of the liver for CT data can be done using the following process:

* Select the `Liver In` segment
* Select the `Segment CT Liver` tool
* Select the volumes ROI in the `ROI` combo box
* Toggle the visibility of the ROI
* Shrink the ROI until it roughly encompasses the volume's liver
* Click on apply
* Correct the segmented liver if necessary using the `Scissors`, `Margin` and `Smoothing` tools.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/liver_tab_ai_segmentation.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/liver_tab_ai_segmentation_result.png" width="800"/>

### Portal veins segmentation

The portal veins segmentation is split into two tabs.

The `Portal Veins` tab is used to initialize the segmentation of the vessels using a vessel intersection tree. First the
vessel tree needs to be constructed by selecting the vessels branching nodes in the views. To place the nodes, click in
the tree on the intersection to be placed. Then click in the 2D or 3D view to place the markup node.

The tree is constructed in a depth first manner. First the root of the tree should be selected, then each intersection
should be selected until the end of the vessel is reached.

Hovering over an item of the tree will display an image indicating the position of the node in the tree.
Clicking on the `Show Current Node Placement Help` will display the image of the position of the current node being
placed.

Edition of the nodes position is done using the `Unlock Node Position` button. This mode is enabled while the button is
checked. It can be disabled by pressing the `Escape` keyboard key.

The nodes can be deleted in the left panel by either clicking the `delete icon` or by pressing the `delete` keyboard
key.

Intermediary nodes can be placed to improve the vessel extraction by clicking on the `Insert before` button in the tree.

Once every node has been placed, the vessels can be extracted from the constructed tree using the
`Extract Vessels from node tree` button. The parameters of the vesselness can be edited to refine the extraction of the
vessels.

After the portal vessels have been extracted, the segmentation can be refined using the `Portal Veins Edit` tab. This
tab uses the segmentation editor and allows for refining the overall portal vein segmentation using the segment editor
tools.

After the portal vein volume has been edited, click on the `Proceed to vessel splitting` button. This button will
extract the center line for each portion of the portal vessels and will create one empty segment per vessel branch. The
scissors tool will be selected automatically and will allow for splitting the overall portal vein volume into its
sub-branches.

#### Constructing the portal tree

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/blob/main/RVXLiverSegmentation/Resources/RVXVesselsHelp/vessels_schema_full.png" width="800"/>

* To start the segmentation, click on the `PortalVeinRoot` element in the `Branch Node Name` tree
* Once the portal vein is in `*Placing*` mode, click in the 2D view at the root of the portal vein
* Proceed with placing the other nodes at the intersection of the branches of the portal vein
* To obtain help on the position of a node, hover on the node in the tree to display the node positioning help
* If a node needs to be displaced, click on the node in the tree and unlock its position to displace the point in the 2D
  view.
* Nodes which cannot be placed due to the patient's condition or to the quality of the acquisition can be removed by
  clicking on the bin icon next to the point.
* Once all the points in the tree are placed, click on the `Extract Vessels from node tree` to proceed with the
  extraction

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_tab_help.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_tab.png" width="800"/>

#### Extracting and segmenting the portal tree

The vessel tree segmentation is based on the following operations :

* A region of interest is selected around the defined tree nodes to improve the processing time
* A Hessian filter is applied on the region of interest to improve the contrast of vessel like structures in the ROI
* A level set segmentation is applied on the Hessian enhanced volume using the branch extremities as seed points

To proceed with the segmentation :

* After clicking on the `Extract Vessels from node tree`, the segmented tree is displayed in the 2D and 3D view
* The segmentation can be modified by changing the parameters of the segmentation, by displacing the control points or
  by adding additional control points in between branch extremities
    * To update the vessel segmentation, click on the `Extract Vessels from node tree`.
    * To modify the Hessian parameters, unfold the `Vesselness Filter Options`. Two options are available for the
      Hessian filtering : VMTK's vesselness filter and Sato's Hessian Filter.
    * To visualize the Hessian filter's results click on the `Show vesselness volume` checkbox
    * To Switch between VTMK and Sato's vesselness filter, toggle the `Use VTMK Vesselness` option
    * For more information on Hessian filters, please refer to [Vesselness filters: A survey with benchmarks applied to
      liver imaging](https://hal.archives-ouvertes.fr/hal-02544493/document)

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_tab_extract_vessels.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_tab_result.png" width="800"/>

#### Editing the portal tree

* Once the extracted vessel tree is satisfying, click on the `Portal Veins Edit` tab to proceed with editing the vessel
  tree.
* This step allows to clean up the whole segmentation using the segment editor's tools.
* When the segmentation is satisfying, click on the `Proceed to vessel splitting` button to split the different branches

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_edit_tab.png" width="800"/>

#### Splitting the portal tree

* After clicking on the `Proceed to vessel splitting` button, one segment per branch node is created
* The `Scissors` tool is preconfigured and allows to select the segmentation in the 3D view and add the selected area to
  the selected segment
* Click on each node successively and add the segment's volume using the `Scissors` tool
* You can hide the segments once the split is done to allow for better visibility in the 3D view
* After every segment has been split, the portal vein segmentation is done

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_edit_split.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_edit_split_result.png" width="800"/>

### IVC veins segmentation

The IVC vein segmentation principle is identical as the portal vein segmentation but for the IVC veins.
For more information on each step, please refer to [Portal veins segmentation](#Portal-veins-segmentation)

#### Constructing the IVC tree

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/blob/main/RVXLiverSegmentation/Resources/RVXVesselsHelp/vessels_schema_full.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/ivc_vein_tab.png" width="800"/>

#### Extracting and segmenting the IVC tree

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/ivc_vein_tab_result.png" width="800"/>

#### Editing the IVC tree

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/ivc_vein_tab_edit.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/ivc_vein_tab_edit_result.png" width="800"/>

### Tumor segmentation

The `Tumor` tab allows for annotating the portions of the liver which present any tumors. It uses the segment editor
configured with two segments.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/tumor_export_tab.png" width="800"/>

### Exporting the results

To export the annotation results, navigate to the last tab (the `Tumor` tab) and click on
the `Export all segmented volumes`
button. A dialog will open querying the location where the results need to be saved.

The following results will be saved :

* Liver label map and model
* Portal vein label map, model and center-lines
* Portal vein tree intersection positions (fiducial CSV, adjacent matrix and [DGtal](https://dgtal.org/) compatible
  format)
* IVC vein label map, model and center-lines
* IVC vein tree intersection positions (fiducial CSV, adjacent matrix and [DGtal](https://dgtal.org/) compatible format)
* Tumor label map
* Slicer scene as .MRB

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/tumor_export_tab_export_click.png" width="800"/>

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/tumor_export_tab_export_result.png" width="800"/>

## Developers

### Manually installing the plugin

The plugin depends on the VMTK and the extra segmentation editor effects extensions. Extensions can be installed in
Slicer3D using
the [extension manager]( https://slicer.readthedocs.io/en/latest/user_guide/extensions_manager.html#install-extensions).

Once VMTK was installed, the plugin can be installed by going to :
Edit > Application Settings > Modules > Additional module paths

The RVXLiverSegmentation and RVXLiverSegmentationEffect directories need to be added to the path list.

When first loading the plugin, a button will be displayed to download the required Python packages. After the download,
the application will be restarted and the plugin will be ready for usage and development.

### Testing

To verify the plugin install, the unit tests of the plugin can be run by enabling Slicer developer mode. To enable the
developer mode go to :
Edit > Application Settings > Developer

Then tick the `Enable developer mode` check box. The application may need to be restarted for this modification to be
taken into account.

To run the unit tests, open the RVesselX plugin, expand the `Reload & Test` menu and click on the `Reload and Test`
button.

To visualize the test results, open the Python console by going to :
View > Python Interactor

The number and the result of the tests will be displayed in the console. Should any of the test fail, please don't
hesitate to [open an issue](https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/issues) or contact us through
the [Slicer forum](https://discourse.slicer.org).

### Contributing

This project welcomes contributions. If you want more information about how you can contribute, please refer to
the [CONTRIBUTING.md file](CONTRIBUTING.md).