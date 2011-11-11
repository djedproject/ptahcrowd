import os, transaction
import ptah, ptah.crowd
from ptah import config
from ptah.authentication import AuthInfo
from pyramid.testing import DummyRequest

from base import Base


class Principal(object):

    def __init__(self, uri, name, login):
        self.uri = uri
        self.name = name
        self.login = login


class TestValidation(Base):

    def test_validation_auth_checker_validation(self):
        from ptah.crowd.validation import validationAndSuspendedChecker

        principal = Principal('1', 'user', 'user')

        props = ptah.crowd.get_properties(principal.uri)
        props.validated = False

        # validation disabled
        info = AuthInfo(True, principal)
        ptah.crowd.CONFIG['validation'] = False
        self.assertTrue(validationAndSuspendedChecker(info))
        transaction.commit()

        info = AuthInfo(True, principal)
        ptah.crowd.CONFIG['allow-unvalidated'] = False
        self.assertTrue(validationAndSuspendedChecker(info))
        transaction.commit()

        # validation enabled
        info = AuthInfo(True, principal)
        ptah.crowd.CONFIG['validation'] = True
        ptah.crowd.CONFIG['allow-unvalidated'] = False
        self.assertFalse(validationAndSuspendedChecker(info))
        self.assertEqual(info.message, 'Account is not validated.')
        transaction.commit()

        info = AuthInfo(True, principal)
        ptah.crowd.CONFIG['allow-unvalidated'] = True
        self.assertTrue(validationAndSuspendedChecker(info))
        transaction.commit()

        # validated
        props = ptah.crowd.get_properties(principal.uri)
        props.validated = True
        transaction.commit()

        info = AuthInfo(True, principal)
        ptah.crowd.CONFIG['validation'] = True
        self.assertTrue(validationAndSuspendedChecker(info))

    def test_validation_auth_checker_suspended(self):
        from ptah.authentication import AuthInfo
        from ptah.crowd.validation import validationAndSuspendedChecker

        principal = Principal('2', 'user', 'user')

        props = ptah.crowd.get_properties(principal.uri)
        props.validated = True
        props.suspended = False

        info = AuthInfo(True, principal)
        self.assertTrue(validationAndSuspendedChecker(info))

        props.suspended = True
        transaction.commit()

        info = AuthInfo(True, principal)
        self.assertFalse(validationAndSuspendedChecker(info))
        self.assertEqual(info.message, 'Account is suspended.')

    def test_validation_registered_unvalidated(self):
        from ptah.crowd.provider import CrowdUser

        user = CrowdUser('name', 'login', 'email')

        ptah.crowd.CONFIG['validation'] = True
        config.notify(ptah.events.PrincipalRegisteredEvent(user))

        props = ptah.crowd.get_properties(user.uri)
        self.assertFalse(props.validated)

    def test_validation_registered_no_validation(self):
        from ptah.crowd.provider import CrowdUser

        user = CrowdUser('name', 'login', 'email')

        ptah.crowd.CONFIG['validation'] = False
        config.notify(ptah.events.PrincipalRegisteredEvent(user))

        props = ptah.crowd.get_properties(user.uri)
        self.assertTrue(props.validated)

    def test_validation_added(self):
        from ptah.crowd.provider import CrowdUser

        user = CrowdUser('name', 'login', 'email')

        ptah.crowd.CONFIG['validation'] = False
        config.notify(ptah.events.PrincipalAddedEvent(user))

        props = ptah.crowd.get_properties(user.uri)
        self.assertTrue(props.validated)

        user = CrowdUser('name', 'login', 'email')
        ptah.crowd.CONFIG['validation'] = True
        config.notify(ptah.events.PrincipalAddedEvent(user))

        props = ptah.crowd.get_properties(user.uri)
        self.assertTrue(props.validated)

    def test_validation_initiate(self):
        from ptah.crowd import validation
        from ptah.crowd.provider import CrowdUser

        origValidationTemplate = validation.ValidationTemplate

        class Stub(origValidationTemplate):

            status = ''
            token = None

            def send(self):
                Stub.status = 'Email has been sended'
                Stub.token = self.token

        validation.ValidationTemplate = Stub

        user = CrowdUser('name', 'login', 'email')

        request = self._makeRequest()

        validation.initiate_email_validation(user.email, user, request)
        self.assertEqual(Stub.status, 'Email has been sended')
        self.assertIsNotNone(Stub.token)

        t = ptah.token.service.get_bydata(validation.TOKEN_TYPE, user.uri)
        self.assertEqual(Stub.token, t)

        validation.ValidationTemplate = origValidationTemplate

    def test_validation_template(self):
        from ptah.crowd import validation
        from ptah.crowd.provider import CrowdUser

        origValidationTemplate = validation.ValidationTemplate
        user = CrowdUser('name', 'login', 'email')

        request = self._makeRequest()

        template = validation.ValidationTemplate(
            user, request, email = user.email, token = 'test-token')
        template.update()

        res = template.render()

        self.assertIn(
            "You're close to completing the registration process.", res)
        self.assertIn(
            "http://localhost:8080/validateaccount.html?token=test-token", res)

    def test_validate(self):
        from ptah.crowd import validation
        from ptah.crowd.provider import CrowdUser, Session

        user = CrowdUser('name', 'login', 'email')
        Session.add(user)
        Session.flush()

        t = ptah.token.service.generate(validation.TOKEN_TYPE, user.uri)

        request = DummyRequest()
        self._setRequest(request)

        try:
            validation.validate(request)
        except:
            pass
        self.assertIn(
            "Can't validate email address.", request.session['msgservice'][0])

        props = ptah.crowd.get_properties(user.uri)
        props.validated = False
        request.GET['token'] = t
        request.session.clear()

        try:
            validation.validate(request)
        except:
            pass
        self.assertIn(
            "Account has been successfully validated.",
            request.session['msgservice'][0])

        props = ptah.crowd.get_properties(user.uri)
        self.assertTrue(props.validated)
