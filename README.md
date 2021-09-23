# RVesselX Slicer Liver Anatomy Annotation Plugin

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/1.png" width="800"/>

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

## Manually installing the plugin

The plugin depends on the VMTK and the extra segmentation editor effects extensions. Extensions can be installed in
Slicer3D using the extension manager :
https://www.slicer.org/wiki/Documentation/4.3/SlicerApplication/ExtensionsManager

Once VMTK was installed, the plugin can be installed by going to :
Edit > Application Settings > Modules > Additional module paths

The directory containing this readme file needs to be added to the path list.

When first loading the plugin, a button will be displayed to download the required Python packages. After the download,
the application will be restarted.

## Testing

To verify the plugin install, the unit tests of the plugin can be run by enabling Slicer developer mode. To enable the
developer mode go to :
Edit > Application Settings > Developer

Then tick the `Enable developer mode` check box. The application may need to be restarted for this modification to be
taken into account.

To run the unit tests, open the RVesselX plugin, expand the `Reload & Test` menu and click on the `Reload and Test`
button.

To visualize the test results, open the Python console by going to :
View > Python Interactor

The number and the result of the tests will be displayed in the console.

## Using the Plugin

The plugin can be open by going to the Slicer module list and clicking on `Segmentation>RVX Liver Segmentation` module.

The plugin is built upon the following tabs : Data, Liver, Portal Veins, Portal Veins Edit, IVC Veins, IVC Veins Edit,
Tumors. Navigation between tabs is done either using the arrow buttons at the top of the plugin or by directly clicking
on the tabs.

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

### Liver segmentation

The `Liver Tab` is used to segment the liver volume. Two segments are created by default, the `Liver In` and `Liver Out`
segments.

The `Segment CT Liver` segmentation effect is available for fast segmentation of the liver for CT data. This
segmentation effect is built upon MONAI and PyTorch to provide ML accelerated segmentation for CT data.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/liver_tab.png" width="800"/>

### Portal veins segmentation

The portal veins segmentation is split into two tabs.

The `Portal Veins` tab is used to initialize the segmentation of the vessels using a vessel intersection tree. First the
vessel tree needs to be constructed by selecting the vessels branching nodes in the views. To place the nodes, click in
the tree on the intersection to be placed. Then click in the 2D or 3D view to place the markup node.

The tree is constructed in a depth first manner. First the root of the tree should be selected, then each intersection
should be selected until the end of the vessel is reached.

Edition of the nodes position is done using the `Unlock Node Position` button. This mode is enabled while the button is
checked. It can be disabled by pressing the `Escape` keyboard key.

The nodes can be deleted in the left panel by either clicking the `delete icon` or by pressing the `delete` keyboard
key.

Intermediary nodes can be placed to improve the vessel extraction by clicking on the `Insert before` button in the tree.

Once every node has been placed, the vessels can be extracted from the constructed tree using the
`Extract Vessels from node tree` button. The parameters of the vesselness can be edited to refine the extraction of the
vessels.

After the portal vessels have been extracted, the segmentation can be refined using the `Portal Veins Edit` tab. This
tab uses the segmentation editor and allows for refining the overall portal vein segmentation.

After the portal vein volume has been edited, click on the `Proceed to vessel splitting` button. This button will
extract the center line for each portion of the portal vessels and will create one empty segment per vessel branch. The
scissors tool will be selected automatically and will allow for splitting the overall portal vein volume into its
sub-branches.

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_tab.png" width="800"/>
<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/portal_vein_edit_tab.png" width="800"/>

### IVC veins segmentation

The IVC vein segmentation principle is identical as the portal vein segmentation.

### Tumor segmentation

The `Tumor` tab allows for annotating the portions of the liver which present any tumors. It uses the segment editor
configured with two segments.

### Exporting the results

To export the annotation results, navigate to the last tab (the `Tumor` tab) and click on
the `Export all segmented volumes`
button. A dialog will open querying the location where the results need to be saved.

The following results will be saved :

* Liver label map
* Portal vein label map
* Portal vein tree intersection positions (fiducial CSV and adjacent matrix)
* IVC vein label map
* IVC vein tree intersection positions (fiducial CSV and adjacent matrix)
* Tumor label map
* Slicer scene as .MRB

<img src="https://github.com/R-Vessel-X/SlicerRVXLiverSegmentation/raw/main/Screenshots/tumor_export_tab.png" width="800"/>
