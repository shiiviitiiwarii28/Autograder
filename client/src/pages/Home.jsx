import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROUTES } from '../constants/routes';
import { 
  AcademicCapIcon, 
  CheckCircleIcon, 
  ClockIcon, 
  ChartBarIcon,
  SparklesIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';

const Home = () => {
  const { isAuthenticated, isStudent, isTeacher } = useAuth();
  const navigate = useNavigate();

  const features = [
    {
      icon: AcademicCapIcon,
      title: 'AI-Powered Grading',
      description: 'Advanced AI algorithms grade exams with high accuracy and consistency'
    },
    {
      icon: ClockIcon,
      title: 'Save Time',
      description: 'Reduce grading time by 90% and focus on what matters most - teaching'
    },
    {
      icon: CheckCircleIcon,
      title: 'Fair & Consistent',
      description: 'Eliminate bias and ensure consistent evaluation across all students'
    },
    {
      icon: ChartBarIcon,
      title: 'Detailed Analytics',
      description: 'Get insights into student performance and identify areas of improvement'
    }
  ];

  const handleGetStarted = () => {
    if (isAuthenticated) {
      if (isStudent) {
        navigate(ROUTES.STUDENT_DASHBOARD);
      } else if (isTeacher) {
        navigate(ROUTES.TEACHER_DASHBOARD);
      }
    } else {
      navigate(ROUTES.SIGNUP);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* Header */}
      <header className="fixed top-0 w-full bg-white/80 backdrop-blur-lg border-b border-gray-200 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <SparklesIcon className="h-8 w-8 text-indigo-600" />
              <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                ExamAI
              </span>
            </div>
            
            <nav className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-gray-600 hover:text-indigo-600 transition">Features</a>
              <a href="#how-it-works" className="text-gray-600 hover:text-indigo-600 transition">How It Works</a>
              <a href="#contact" className="text-gray-600 hover:text-indigo-600 transition">Contact</a>
            </nav>

            <div className="flex items-center space-x-4">
              {!isAuthenticated ? (
                <>
                  <Link
                    to={ROUTES.LOGIN}
                    className="text-gray-600 hover:text-indigo-600 font-medium transition"
                  >
                    Login
                  </Link>
                  <Link
                    to={ROUTES.SIGNUP}
                    className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition transform hover:-translate-y-0.5"
                  >
                    Sign Up
                  </Link>
                </>
              ) : (
                <button
                  onClick={handleGetStarted}
                  className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition transform hover:-translate-y-0.5"
                >
                  Dashboard
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <h1 className="text-5xl md:text-7xl font-bold mb-6">
              <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                AI-Powered
              </span>
              <br />
              <span className="text-gray-900">Exam Grading System</span>
            </h1>
            
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Transform the way you grade exams. Our AI technology ensures fast, 
              fair, and accurate evaluation of student answer sheets.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={handleGetStarted}
                className="group px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold hover:shadow-2xl transition transform hover:-translate-y-1 flex items-center space-x-2"
              >
                <span>Get Started</span>
                <ArrowRightIcon className="h-5 w-5 group-hover:translate-x-1 transition" />
              </button>
              
              <a
                href="#how-it-works"
                className="px-8 py-4 bg-white text-indigo-600 rounded-xl font-semibold border-2 border-indigo-600 hover:bg-indigo-50 transition"
              >
                Learn More
              </a>
            </div>

            {/* Stats */}
            <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
              {[
                { value: '98%', label: 'Accuracy' },
                { value: '90%', label: 'Time Saved' },
                { value: '50K+', label: 'Exams Graded' },
                { value: '1000+', label: 'Happy Teachers' }
              ].map((stat, index) => (
                <div key={index} className="bg-white rounded-2xl p-6 shadow-lg">
                  <div className="text-3xl font-bold text-indigo-600 mb-2">{stat.value}</div>
                  <div className="text-gray-600">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Why Choose ExamAI?
            </h2>
            <p className="text-xl text-gray-600">
              Powerful features designed for modern education
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group p-6 rounded-2xl bg-gradient-to-br from-indigo-50 to-purple-50 hover:shadow-2xl transition transform hover:-translate-y-2"
              >
                <feature.icon className="h-12 w-12 text-indigo-600 mb-4 group-hover:scale-110 transition" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-gradient-to-br from-indigo-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600">
              Simple, fast, and efficient
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Upload', description: 'Students upload their answer sheets' },
              { step: '02', title: 'AI Grades', description: 'Our AI evaluates and grades automatically' },
              { step: '03', title: 'Results', description: 'Get instant results with detailed feedback' }
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="inline-block mb-4 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-full text-2xl font-bold">
                  {item.step}
                </div>
                <h3 className="text-2xl font-semibold text-gray-900 mb-2">
                  {item.title}
                </h3>
                <p className="text-gray-600">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-indigo-600 to-purple-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to Transform Your Grading?
          </h2>
          <p className="text-xl text-indigo-100 mb-8">
            Join thousands of educators who are saving time and improving accuracy
          </p>
          <button
            onClick={handleGetStarted}
            className="px-8 py-4 bg-white text-indigo-600 rounded-xl font-semibold hover:shadow-2xl transition transform hover:-translate-y-1"
          >
            Get Started for Free
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <SparklesIcon className="h-8 w-8 text-indigo-400" />
                <span className="text-2xl font-bold">ExamAI</span>
              </div>
              <p className="text-gray-400">
                Revolutionizing exam grading with AI
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#features" className="hover:text-white transition">Features</a></li>
                <li><a href="#how-it-works" className="hover:text-white transition">How It Works</a></li>
                <li><a href="#" className="hover:text-white transition">Pricing</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#" className="hover:text-white transition">About</a></li>
                <li><a href="#" className="hover:text-white transition">Blog</a></li>
                <li><a href="#contact" className="hover:text-white transition">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#" className="hover:text-white transition">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition">Terms</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2025 Autograder. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;