"""Fail-closed publication projection for SCB workplace records.

Only use after legal form has been verified from SCB's juridiskaenheter.
This module does NOT approve public individual-record publication.
"""
PERSON_LABEL="Privatperson"
REDACTED="XXX"

def public_workplace(workplace, legal_unit, *, legal_form_verified=False):
    """Create a display-safe projection. Never publish raw workplace/legal-unit dicts."""
    if not isinstance(workplace,dict):raise TypeError("workplace must be a mapping")
    if not isinstance(legal_unit,dict):legal_unit={}
    form=str(legal_unit.get("jurform") or "").strip()
    # A legal form string alone is not enough: must be verified via SCB entity response.
    trusted=legal_form_verified and bool(form)
    is_physical=trusted and form=="10"
    is_legal=trusted and form!="10"
    if not is_legal:
        return {
            "display_name":PERSON_LABEL if is_physical else "Uppgift skyddad",
            "display_org_number":REDACTED,
            "display_address":None,
            "display_contact":None,
            "display_coordinates":None,
            "legal_form":form if trusted else "okänd",
            "publication_class":"physical_person" if is_physical else "unverified",
        }
    # Deliberately conservative: even legal entities can carry third-party personal details.
    name=legal_unit.get("namn")
    if not isinstance(name,str) or not name.strip():name=workplace.get("ben")
    if not isinstance(name,str) or not name.strip():name="Namn saknas"
    org=legal_unit.get("orgNr")
    if not isinstance(org,str) or not org.strip():org=REDACTED
    return {
        "display_name":name.strip(),
        "display_org_number":org.strip() if isinstance(org,str) else REDACTED,
        "display_address":None,
        "display_contact":None,
        "display_coordinates":None,
        "legal_form":form,
        "publication_class":"legal_entity_needs_publication_review",
    }
