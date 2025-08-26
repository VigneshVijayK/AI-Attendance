from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:
	from wsdiscovery import WSDiscovery
	from onvif import ONVIFCamera
except Exception:
	WSDiscovery = None  # type: ignore
	ONVIFCamera = None  # type: ignore


@dataclass
class OnvifDevice:
	xaddr: str
	types: str
	scopes: str
	ip: Optional[str]


def discover_onvif_devices(timeout: int = 3) -> List[OnvifDevice]:
	if WSDiscovery is None:
		return []
	wsd = WSDiscovery()
	wsd.start()
	services = wsd.searchServices(timeout=timeout)
	devices: List[OnvifDevice] = []
	for s in services:
		ip = None
		try:
			ip = s.getXAddrs()[0].split("//")[-1].split(":")[0]
		except Exception:
			pass
		devices.append(OnvifDevice(xaddr=str(s.getXAddrs()), types=str(s.getTypes()), scopes=str(s.getScopes()), ip=ip))
	wsd.stop()
	return devices


def build_rtsp_from_onvif(host: str, username: str, password: str, port: int = 80) -> Optional[str]:
	"""Attempt to query ONVIF device and return first RTSP URL if available."""
	if ONVIFCamera is None:
		return None
	try:
		cam = ONVIFCamera(host, port, username, password)
		media = cam.create_media_service()
		profiles = media.GetProfiles()
		if not profiles:
			return None
		profile = profiles[0]
		uri = media.GetStreamUri({
			"StreamSetup": {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}},
			"ProfileToken": profile.token,
		})
		return uri.Uri
	except Exception:
		return None





