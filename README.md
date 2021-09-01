# RVesselX Slicer Plugin

<img src="https://github.com/R-Vessel-X/LiverAnatomyAnnotation/raw/main/RVesselX/Resources/Icons/RVesselX.png"/>

<img src="https://github.com/R-Vessel-X/LiverAnatomyAnnotation/raw/main/Screenshots/1.png" width="800"/>


## Introduction

The RVesselX slicer plugin is a plugin for Slicer3D which aims at easing the segmentation of liver, liver vessels and liver tumor from DICOM data for annotation purposes. 
The exported segmentations will then be used in research.

For more information on the R-Vessel-X project, please visit :  
https://anr.fr/Projet-ANR-18-CE45-0018

## Manually installing the plugin

The plugin depends on the VMTK and the extra segmentation editor effects extensions. Extensions can be installed in Slicer3D using the extension manager :
https://www.slicer.org/wiki/Documentation/4.3/SlicerApplication/ExtensionsManager

Once VMTK was installed, the plugin can be installed by going to : 
Edit > Application Settings > Modules > Additional module paths

The directory containing this readme file needs to be added to the path list.

When first loading the plugin, a button will be displayed to download the required Python packages.
After the download, the application will be restarted.

## Testing

To verify the plugin install, the unit tests of the plugin can be run by enabling Slicer developer mode.
To enable the developer mode go to : 
Edit > Application Settings > Developer 

Then tick the `Enable developer mode` check box. The application may need to be restarted for this modification to be taken into account.

To run the unit tests, open the RVesselX plugin, expand the `Reload & Test` menu and click on the `Reload and Test` button. 

To visualize the test results, open the Python console by going to :
View > Python Interactor

The number and the result of the tests will be displayed in the console.

## Using the Plugin

The plugin can be open by going to the Slicer module list and clicking on `Liver Anatomy Annotation>R Vessel X` module.

The plugin is built upon 4 tabs : Data, Liver, Vessels, Tumors.
Navigation between tabs is done either using the arrow buttons at the top of the plugin or by directly clicking on the tabs.

* The `Data Tab` is used to open the patient data. Loading can be done using the `Load DICOM` and the `Load Data` buttons. The input volume needs to be selected using the `Volume` combo box.
* The `Liver Tab` is used to segment the liver volume. Two segments are created by default, the `Liver In` and `Liver Out` segments.
* The `Vessels Tab` is used to segment the vessels volume. First the vessel tree needs to be constructed by selecting the vessels branching nodes in the views. Then the vessels can be extracted from the constructed tree using the `Extract Vessels from node tree` button.
	* The tree is constructed in a depth first manner. First the root of the tree should be selected, then each intersection should be selected until the end of the vessel is reached.
When the end of the vessel is reached, the previous intersection should be selected in the left panel tree and the other vessel starting from this intersection should be followed using the same method.
If an intersection has been missed, a node can be inserted before another one by holding the `Shift` Keyboard key and clicking on the node before which the new node should be inserted.
	*  Creation of new nodes is done using the `Add branching node` button. This mode is enabled while the button is checked. It can be disabled by pressing the `Escape` keyboard key.
Nodes are added by either left clicking in the slicer vue or the 3D vue.
	* Edition of the nodes position is done using the `Edit branching node` button. This mode is enabled while the button is checked. It can be disabled by pressing the `Escape` keyboard key.
	* The nodes can be deleted in the left panel by either clicking the `delete icon` or by pressing the delete keyboard key.
	* The nodes can be reordered in the left panel by drag and drop
* The `TumorTab` is used to segment the tumor volume if any. Two segments are created by default, the `Tumor` and `Not Tumor` segments.

Once all the volumes are segmented, they can be exported to a directory using the `Export all segmented volumes` button.