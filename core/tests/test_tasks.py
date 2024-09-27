from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from core.models import Subscription, User
from core.tasks import refresh_order_limits
from unittest.mock import patch, MagicMock

class RefreshOrderLimitsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user; the signal will automatically create a Subscription
        cls.user = User.objects.create_user(username='testuser', password='password')

        # Retrieve the Subscription created by the signal
        cls.subscription = Subscription.objects.get(user=cls.user)

        # Modify the Subscription as needed for tests
        cls.subscription.plan = 'STARTER'
        cls.subscription.order_count = 10
        cls.subscription.next_refresh_date = timezone.now() - timedelta(days=1)  # Set to yesterday
        cls.subscription.status = 'active'
        cls.subscription.stripe_subscription_id = 'sub_test123'
        cls.subscription.save()

    @patch('core.tasks.stripe.Subscription.retrieve')
    def test_refresh_order_limits(self, mock_retrieve):
        # Mock the Stripe API retrieve call to return an active subscription
        mock_stripe_sub = MagicMock()
        mock_stripe_sub.status = 'active'
        mock_retrieve.return_value = mock_stripe_sub

        # Ensure initial conditions
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.order_count, 10)
        self.assertTrue(self.subscription.next_refresh_date < timezone.now())

        # Execute the Celery task
        refresh_order_limits()

        # Refresh from the database
        self.subscription.refresh_from_db()

        # Verify that order_count is reset
        self.assertEqual(self.subscription.order_count, 0)

        # Verify that next_refresh_date is updated to one month ahead
        expected_new_date = timezone.now() + timedelta(days=30)
        delta = self.subscription.next_refresh_date - expected_new_date
        self.assertTrue(abs(delta.total_seconds()) < 60)  # Within 1 minute

    @patch('core.tasks.stripe.Subscription.retrieve')
    def test_subscription_inactive_if_stripe_inactive(self, mock_retrieve):
        # Modify the Subscription for the test
        self.subscription.next_refresh_date = timezone.now() - timedelta(days=1)
        self.subscription.save()

        # Mock Stripe subscription retrieval to return inactive status
        mock_stripe_sub = MagicMock()
        mock_stripe_sub.status = 'canceled'
        mock_retrieve.return_value = mock_stripe_sub

        # Execute the Celery task
        refresh_order_limits()

        # Refresh from the database
        self.subscription.refresh_from_db()

        # Verify that the subscription status is set to inactive
        self.assertEqual(self.subscription.status, 'inactive')

    @patch('core.tasks.stripe.Subscription.retrieve')
    def test_handle_stripe_error_gracefully(self, mock_retrieve):
        # Modify the Subscription for the test
        self.subscription.next_refresh_date = timezone.now() - timedelta(days=1)
        self.subscription.save()

        # Mock Stripe subscription retrieval to raise an error
        mock_retrieve.side_effect = Exception('Stripe error')

        # Execute the Celery task
        refresh_order_limits()

        # Refresh from the database
        self.subscription.refresh_from_db()

        # Verify that the subscription status remains unchanged
        self.assertEqual(self.subscription.status, 'active')
        self.assertEqual(self.subscription.order_count, 10)
