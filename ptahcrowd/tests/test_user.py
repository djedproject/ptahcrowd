import transaction
import ptah
from ptah.testing import PtahTestCase
from pyramid.httpexceptions import HTTPFound, HTTPForbidden


class TestCreateUser(PtahTestCase):

    _includes = ('ptahcrowd',)

    def test_create_user_back(self):
        from ptahcrowd.module import CrowdModule
        from ptahcrowd.user import CreateUserForm

        request = self.make_request(
            POST = {'form.buttons.back': 'Back'})
        mod = CrowdModule(None, request)

        view = CreateUserForm(mod, request)
        res = view()
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '.')

    def test_create_user_error(self):
        from ptahcrowd.module import CrowdModule
        from ptahcrowd.user import CreateUserForm

        request = self.make_request(
            POST = {'form.buttons.create': 'Create'})
        request.POST[CreateUserForm.csrf_name] = \
            request.session.get_csrf_token()
        mod = CrowdModule(None, request)

        view = CreateUserForm(mod, request)
        view.update_form()
        self.assertIn(
            'Please fix indicated errors.',
            request.render_messages())

    def test_create_user(self):
        from ptahcrowd.module import CrowdModule
        from ptahcrowd.user import CreateUserForm

        request = self.make_request(
            POST = {'username': 'NKim',
                    'email': 'ptah@ptahproject.org',
                    'password': '12345',
                    'validated': 'false',
                    'suspended': 'true',
                    'form.buttons.create': 'Create'})
        request.POST[CreateUserForm.csrf_name] = \
            request.session.get_csrf_token()

        mod = CrowdModule(None, request)

        view = CreateUserForm(mod, request)
        res = view()

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '.')
        self.assertIn('User has been created.', request.render_messages())
        transaction.commit()

        user = ptah.auth_service.get_principal_bylogin('ptah@ptahproject.org')
        self.assertEqual(user.username, 'NKim')
        self.assertEqual(user.email, 'ptah@ptahproject.org')
        self.assertTrue(user.suspended)
        self.assertFalse(user.validated)


class TestModifyUser(PtahTestCase):

    _includes = ('ptahcrowd',)

    def _user(self):
        from ptahcrowd.provider import CrowdUser
        user = CrowdUser(username='username', email='ptah@local')
        user.__type__.add(user)
        return user

    def test_modify_user_back(self):
        from ptahcrowd.user import ModifyUserForm

        user = self._user()

        request = self.make_request(
            POST = {'form.buttons.back': 'Back'})

        view = ModifyUserForm(user, request)
        res = view()

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '..')

    def test_modify_user_forbidden(self):
        from ptahcrowd.user import ModifyUserForm

        user = self._user()

        request = self.make_request(
            POST = {'form.buttons.modify': 'Modify',
                    'username': 'NKim',
                    'email': 'ptah@ptahproject.org',
                    'password': '12345',
                    'validated': 'false',
                    'suspended': 'true',
                    })

        view = ModifyUserForm(user, request)
        res = None
        try:
            view.update_form()
        except Exception as err:
            res = err

        self.assertIsInstance(res, HTTPForbidden)
        self.assertEqual(str(res), 'Form authenticator is not found.')

    def test_modify_user_error(self):
        from ptahcrowd.user import ModifyUserForm

        user = self._user()

        request = self.make_request(
            POST = {'form.buttons.modify': 'Modify'})

        view = ModifyUserForm(user, request)
        view.csrf = False
        view.update_form()

        self.assertIn(
            'Please fix indicated errors.',
            request.render_messages())

    def test_modify_user(self):
        from ptahcrowd.user import ModifyUserForm

        user = self._user()
        request = self.make_request(
            POST = {'form.buttons.modify': 'Modify',
                    'username': 'NKim',
                    'email': 'ptah@ptahproject.org',
                    'password': '12345',
                    'validated': 'false',
                    'suspended': 'true'})

        view = ModifyUserForm(user, request)
        view.csrf = False
        view.update_form()

        self.assertEqual(user.username, 'NKim')
        self.assertEqual(user.email, 'ptah@ptahproject.org')

    def test_modify_user_remove(self):
        from ptahcrowd.user import ModifyUserForm

        user = self._user()

        request = self.make_request(
            POST = {'form.buttons.remove': 'Remove'})

        view = ModifyUserForm(user, request)
        view.csrf = False
        res = view()

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '..')

        user = ptah.resolve(user.__uri__)
        self.assertIsNone(user)
