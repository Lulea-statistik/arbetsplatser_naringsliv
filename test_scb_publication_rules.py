import unittest
from scb_publication_rules import public_workplace

class PublicationRules(unittest.TestCase):
    def test_physical_person_hides_every_identifier(self):
        row={"ben":"Personens namn","peOrgNr":"197001011234","belagenhetsadress":{"bGatuAdress":"Hemvägen 1"}}
        obj=public_workplace(row,{"jurform":"10","namn":"Personens namn","orgNr":"197001011234"},legal_form_verified=True)
        self.assertEqual(obj["display_name"],"Privatperson")
        self.assertEqual(obj["display_org_number"],"XXX")
        self.assertIsNone(obj["display_address"])
        self.assertNotIn("197001011234",str(obj))
        self.assertNotIn("Hemvägen",str(obj))
    def test_unknown_is_hidden(self):
        obj=public_workplace({"ben":"Okänt företag"},{},legal_form_verified=False)
        self.assertEqual(obj["display_name"],"Uppgift skyddad")
        self.assertEqual(obj["display_org_number"],"XXX")
    def test_unverified_legal_code_is_hidden(self):
        obj=public_workplace({"ben":"AB Exempel"},{"jurform":"49","namn":"AB Exempel","orgNr":"5560000000"})
        self.assertEqual(obj["display_name"],"Uppgift skyddad")
    def test_legal_entity_display_fields(self):
        obj=public_workplace({"ben":"Arbetsställe"},{"jurform":"49","namn":"Exempel AB","orgNr":"5560000000"},legal_form_verified=True)
        self.assertEqual(obj["display_name"],"Exempel AB")
        self.assertEqual(obj["display_org_number"],"5560000000")
        self.assertIsNone(obj["display_address"])
if __name__=="__main__":unittest.main()
