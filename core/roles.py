from enum import Enum


class UserRole(str, Enum):
    CEO = "CEO"
    ANALYST = "Analyst"
    ADMIN = "Admin"


ROLE_PAGES = {
    UserRole.ADMIN: [
        "1_Home",
        "2_New_Review",
        "3_Data_Input",
        "4_Scoring_Dashboard",
        "5_Benchmarking",
        "6_SWOT",
        "7_Recommendations",
        "8_Admin_Config",
        "9_Advisor.py"
    ],

    UserRole.ANALYST: [
        "1_Home",
        "2_New_Review",
        "3_Data_Input",
        "4_Scoring_Dashboard",
        "5_Benchmarking",
        "6_SWOT",
        "7_Recommendations"
    ],

    UserRole.CEO: [
        "1_Home",
        "4_Scoring_Dashboard",
        "5_Benchmarking",
        "7_Recommendations",
        "9_Advisor.py"
    ]
}
