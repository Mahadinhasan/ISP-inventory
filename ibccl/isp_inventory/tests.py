from django.test import TestCase
from isp_inventory.models import Material, UsedMaterial, RefundableMaterial
from isp_inventory.views import dashboard, materials_view, used_materials_view, refundable_materials_view, damaged_materials_view, report_damage_auto
from django.contrib.auth.models import User
from django.urls import reverse

# Create your tests here.
class InventoryTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Create test materials
        self.material1 = Material.objects.create(name='Material 1', description='Test material 1', quantity=10)
        self.material2 = Material.objects.create(name='Material 2', description='Test material 2', quantity=5)

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_materials_view(self):
        response = self.client.get(reverse('materials'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Material 1')
        self.assertContains(response, 'Material 2')

    def test_used_materials_view(self):
        UsedMaterial.objects.create(material=self.material1, user=self.user, quantity=2)
        response = self.client.get(reverse('used_materials'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Used Materials')
        self.assertContains(response, 'Material 1')

    def test_refundable_materials_view(self):
        RefundableMaterial.objects.create(material=self.material2, user=self.user, quantity=1)
        response = self.client.get(reverse('refundable_materials'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Refundable Materials')
        self.assertContains(response, 'Material 2')

    def test_damaged_materials_view(self):
        response = self.client.get(reverse('damaged_materials'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Damaged Materials')

    def test_report_damage_auto(self):
        response = self.client.post(reverse('report_damage_auto'), {'material_id': self.material1.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Damage reported successfully')
        self.material1.refresh_from_db()
        self.assertEqual(self.material1.quantity, 9)