#-----------------------------------------------------------------------------
set(MODULE_NAME RVXLiverSegmentation)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
    ${MODULE_NAME}.py
    ${MODULE_NAME}Lib/__init__.py
    ${MODULE_NAME}Lib/DataWidget.py
    ${MODULE_NAME}Lib/ExtractVesselStrategies.py
    ${MODULE_NAME}Lib/RVXLiverSegmentationLogic.py
    ${MODULE_NAME}Lib/RVXLiverSegmentationUtils.py
    ${MODULE_NAME}Lib/SegmentWidget.py
    ${MODULE_NAME}Lib/VerticalLayoutWidget.py
    ${MODULE_NAME}Lib/VesselBranchTree.py
    ${MODULE_NAME}Lib/VesselBranchWizard.py
    ${MODULE_NAME}Lib/VesselSegmentEditWidget.py
    ${MODULE_NAME}Lib/VesselWidget.py
    ${MODULE_NAME}Lib/VesselHelpWidget.py
    ${MODULE_NAME}Test/__init__.py
    ${MODULE_NAME}Test/ExtractVesselStrategyTestCase.py
    ${MODULE_NAME}Test/ModuleLogicTestCase.py
    ${MODULE_NAME}Test/TestUtils.py
    ${MODULE_NAME}Test/VesselBranchTreeTestCase.py
    ${MODULE_NAME}Test/VesselBranchWizardTestCase.py
    ${MODULE_NAME}Test/VesselSegmentEditWidgetTestCase.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Icons/3D_IRCAD_B_5_Liver.png
  Resources/RVXVesselsHelp/vessels_schema_full.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_ivc.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_ivc_root.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_left.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_left_left.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_left_right.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_median.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_median_left.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_median_right.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_opt_1.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_opt_2.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_opt_3.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_right.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_right_left.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_right_right.png
  Resources/RVXVesselsHelp/vessels_schema_ivc_veins.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_ii.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_iii.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_iv.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_left.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_opt_1.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_opt_2.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_opt_3.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_portal_root.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_portal_vein.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_right.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_right_anterior.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_right_posterior.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_v.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_vi.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_vii.png
  Resources/RVXVesselsHelp/vessels_schema_portal_veins_viii.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
