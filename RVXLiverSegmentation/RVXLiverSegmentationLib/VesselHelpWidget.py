from qt import QToolTip, QCursor

from RVXLiverSegmentationLib import resourcesPath, VeinId
from enum import Enum, auto, unique


@unique
class VesselHelpType(Enum):
  Portal = auto()
  IVC = auto()


class VesselHelpWidget:
  def __init__(self, helpType):
    self._lastVeinType = None
    self._helpDict = self._portalHelpPathDict() if helpType == VesselHelpType.Portal else self._ivcHelpPathDict()
    self._default = self._helpDict[helpType]
    self._helpImagePath = self.getHelpImagePath(None)

  def updateHelp(self, veinType):
    self._lastVeinType = veinType

  def showHelp(self):
    QToolTip.showText(QCursor.pos(), self.tooltipImageUrl(self._lastVeinType))

  def tooltipImageUrl(self, veinType):
    return f"<img src='{self.getHelpImagePath(veinType)}' width='600' height='600'>"

  def getHelpImagePath(self, veinType):
    return self._helpDict.get(veinType, self._default)

  def _helpPath(self):
    return resourcesPath().joinpath("RVXVesselsHelp")

  def _portalHelpPathDict(self):
    return {VesselHelpType.Portal: self._helpPath().joinpath("vessels_schema_portal_veins.png"),
            VeinId.portalVeinRoot: self._helpPath().joinpath("vessels_schema_portal_veins_portal_root.png"),
            VeinId.portalVein: self._helpPath().joinpath("vessels_schema_portal_veins_portal_vein.png"),
            VeinId.leftPortalVein: self._helpPath().joinpath("vessels_schema_portal_veins_left.png"),
            VeinId.rightPortalVein: self._helpPath().joinpath("vessels_schema_portal_veins_right.png"),
            VeinId.anteriorBranch: self._helpPath().joinpath("vessels_schema_portal_veins_right_anterior.png"),
            VeinId.posteriorBranch: self._helpPath().joinpath("vessels_schema_portal_veins_right_posterior.png"),
            VeinId.segmentalBranch_2: self._helpPath().joinpath("vessels_schema_portal_veins_ii.png"),
            VeinId.segmentalBranch_3: self._helpPath().joinpath("vessels_schema_portal_veins_iii.png"),
            VeinId.segmentalBranch_4: self._helpPath().joinpath("vessels_schema_portal_veins_iv.png"),
            VeinId.segmentalBranch_5: self._helpPath().joinpath("vessels_schema_portal_veins_v.png"),
            VeinId.segmentalBranch_6: self._helpPath().joinpath("vessels_schema_portal_veins_vi.png"),
            VeinId.segmentalBranch_7: self._helpPath().joinpath("vessels_schema_portal_veins_vii.png"),
            VeinId.segmentalBranch_8: self._helpPath().joinpath("vessels_schema_portal_veins_viii.png"),
            VeinId.portalOptional_1: self._helpPath().joinpath("vessels_schema_portal_veins_opt_1.png"),
            VeinId.portalOptional_2: self._helpPath().joinpath("vessels_schema_portal_veins_opt_2.png"),
            VeinId.portalOptional_3: self._helpPath().joinpath("vessels_schema_portal_veins_opt_3.png")}

  def _ivcHelpPathDict(self):
    return {VesselHelpType.IVC: self._helpPath().joinpath("vessels_schema_ivc_veins.png"),
            VeinId.inferiorCavaVeinRoot: self._helpPath().joinpath("vessels_schema_ivc_ivc_root.png"),
            VeinId.inferiorCavaVein: self._helpPath().joinpath("vessels_schema_ivc_ivc.png"),
            VeinId.leftHepaticVein: self._helpPath().joinpath("vessels_schema_ivc_left.png"),
            VeinId.leftHepaticVein_LeftBranch: self._helpPath().joinpath("vessels_schema_ivc_left_left.png"),
            VeinId.leftHepaticVein_RightBranch: self._helpPath().joinpath("vessels_schema_ivc_left_right.png"),
            VeinId.medianHepaticVein: self._helpPath().joinpath("vessels_schema_ivc_median.png"),
            VeinId.medianHepaticVein_LeftBranch: self._helpPath().joinpath("vessels_schema_ivc_median_left.png"),
            VeinId.medianHepaticVein_RightBranch: self._helpPath().joinpath("vessels_schema_ivc_median_right.png"),
            VeinId.rightHepaticVein: self._helpPath().joinpath("vessels_schema_ivc_right.png"),
            VeinId.rightHepaticVein_LeftBranch: self._helpPath().joinpath("vessels_schema_ivc_right_left.png"),
            VeinId.rightHepaticVein_RightBranch: self._helpPath().joinpath("vessels_schema_ivc_right_right.png"),
            VeinId.ivcOptional_1: self._helpPath().joinpath("vessels_schema_ivc_opt_1.png"),
            VeinId.ivcOptional_2: self._helpPath().joinpath("vessels_schema_ivc_opt_2.png"),
            VeinId.ivcOptional_3: self._helpPath().joinpath("vessels_schema_ivc_opt_3.png")}
