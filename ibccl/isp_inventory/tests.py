from django.test import TestCase
from isp_inventory.models import Material, UsedMaterial, RefundableMaterial, MaterialRequest, RefundableMaterialUsage
from django.contrib.auth.models import User
from django.urls import reverse

class InventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Create test materials
        self.material1 = Material.objects.create(name='Material 1', notes='Test material 1', quantity=10)
        self.material2 = Material.objects.create(name='Material 2', notes='Test material 2', quantity=5)

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard'))
        # Can be 200 or 302 redirect (if profile redirect applies)
        self.assertIn(response.status_code, [200, 302])

    def test_materials_view(self):
        response = self.client.get(reverse('materials'))
        self.assertEqual(response.status_code, 200)

    def test_used_materials_view(self):
        UsedMaterial.objects.create(material=self.material1, technician=self.user, quantity=2)
        response = self.client.get(reverse('used_materials'))
        self.assertEqual(response.status_code, 200)

    def test_refundable_materials_view(self):
        RefundableMaterial.objects.create(branch_user=self.user, material_name=self.material2.name, quantity=1)
        response = self.client.get(reverse('refundable_materials'))
        self.assertEqual(response.status_code, 200)

    def test_get_refundable_material_usage_api(self):
        rf = RefundableMaterial.objects.create(branch_user=self.user, material_name=self.material2.name, quantity=5)
        usage = RefundableMaterialUsage.objects.create(refundable_material=rf, used_by=self.user, materials_quantity=2, client_name='Client A')
        response = self.client.get(reverse('get_refundable_material_usage_api', args=[usage.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Client A')

    def test_damaged_materials_view(self):
        response = self.client.get(reverse('damaged_materials'))
        self.assertEqual(response.status_code, 200)

    def test_report_damage_auto(self):
        MaterialRequest.objects.create(
            requester=self.user,
            material=self.material1,
            quantity=5,
            status='Received'
        )
        response = self.client.post(reverse('report_damage_auto'), {'material_id': self.material1.id, 'quantity': 1})
        self.assertEqual(response.status_code, 200)