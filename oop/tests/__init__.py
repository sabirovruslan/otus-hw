import unittest

from tests.test_fields import CharFieldTest, ArgumentsFieldTest, EmailFieldTest, PhoneFieldTest


def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(CharFieldTest))
    test_suite.addTest(unittest.makeSuite(ArgumentsFieldTest))
    test_suite.addTest(unittest.makeSuite(EmailFieldTest))
    test_suite.addTest(unittest.makeSuite(PhoneFieldTest))
    return test_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
