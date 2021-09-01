cmake_minimum_required(VERSION 3.13.4)

project(RVesselX)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/R-Vessel-X/LiverAnatomyAnnotation")
set(EXTENSION_CATEGORY "Liver Anatomy Annotation")
set(EXTENSION_CONTRIBUTORS "Lucie Macron (Kitware SAS), Thibault Pelletier (Kitware SAS), Camille Huet (Kitware SAS)")
set(EXTENSION_DESCRIPTION "Liver and hepatic vessels annotation plugin")
set(EXTENSION_ICONURL "https://github.com/R-Vessel-X/LiverAnatomyAnnotation/raw/main/RVesselX/Resources/Icons/RVesselX.png")
set(EXTENSION_SCREENSHOTURLS "https://github.com/R-Vessel-X/LiverAnatomyAnnotation/raw/main/Screenshots/1.png")
set(EXTENSION_DEPENDS "SlicerVMTK MarkupsToModel SegmentEditorExtraEffects") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(RVesselX)
add_subdirectory(RVesselXLiverSegmentationEffect)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
