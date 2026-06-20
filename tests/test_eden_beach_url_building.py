import unittest

from eden_beach_integration import EdenBeachAPIClient


class EdenBeachURLBuildingTests(unittest.TestCase):
    def test_build_request_url_from_host_only_base(self):
        url = EdenBeachAPIClient._build_request_url(
            "https://api.stayflexi.com",
            "/reservation/navigationGetRoomBookings",
        )
        self.assertEqual(
            url,
            "https://api.stayflexi.com/core/apiv1/cmservice/reservation/navigationGetRoomBookings",
        )

    def test_build_request_url_from_cmservice_base(self):
        url = EdenBeachAPIClient._build_request_url(
            "https://api.stayflexi.com/core/apiv1/cmservice/",
            "reservation/navigationGetRoomBookings",
        )
        self.assertEqual(
            url,
            "https://api.stayflexi.com/core/apiv1/cmservice/reservation/navigationGetRoomBookings",
        )


if __name__ == "__main__":
    unittest.main()
