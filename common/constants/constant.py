from dotenv import variables
ACCESS_TOKEN_EXPIRATION_TIME=60
ALGORITHM="HS256"

### resend template ids
class BaseResendStructure:
    id: str

### Wait List
class WaitListVariables:
    first_name: str
class WailtListTemplateType(BaseResendStructure):
    variables: WaitListVariables

### Template ids
TEMPLATE_IDS = {
    "waitlist_id": "74a99303-28ed-4eac-a9a9-3b5cfbf3066a",
}
