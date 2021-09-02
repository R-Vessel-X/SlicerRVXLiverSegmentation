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
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
